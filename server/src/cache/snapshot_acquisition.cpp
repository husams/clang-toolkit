#include "cache_state.hpp"

#include <algorithm>
#include <exception>
#include <stdexcept>
#include <utility>

namespace ctk::cache {
namespace {

// Waiter accounting is independent of flight locking, so stats can be read
// while a caller sleeps without holding the metadata mutex.
class WaitingAcquisition {
public:
  WaitingAcquisition(std::mutex &metadata, std::size_t &count)
      : metadata_(metadata), count_(count) {
    std::lock_guard lock(metadata_);
    ++count_;
  }
  ~WaitingAcquisition() {
    std::lock_guard lock(metadata_);
    --count_;
  }
  WaitingAcquisition(const WaitingAcquisition &) = delete;
  WaitingAcquisition &operator=(const WaitingAcquisition &) = delete;

private:
  std::mutex &metadata_;
  std::size_t &count_;
};

// Wait only on the flight's mutex. Return owned results before any subsequent
// metadata lookup, so cancellation and slow loaders cannot block cache stats.
detail::FlightResult await_flight(const std::shared_ptr<detail::Flight> &flight,
                                  std::stop_token cancellation) {
  std::unique_lock lock(flight->mutex);
  if (!flight->ready.wait(lock, cancellation, [&] { return flight->done; }))
    throw AcquisitionCancelled();
  return {flight->snapshot, flight->publication_epoch, flight->error};
}

// Keep immutable manifest order while preparing one advisory hint per path.
// Copies, sorting and allocations here must happen before metadata locking.
detail::PreparedSnapshot
prepare_snapshot(SnapshotPtr snapshot,
                 const std::shared_ptr<detail::ProfileEntry> &profile) {
  detail::PreparedSnapshot prepared;
  prepared.snapshot = std::move(snapshot);
  prepared.observations = prepared.snapshot->inputs;
  std::ranges::sort(prepared.observations, {}, &InputObservation::path);
  prepared.observations.erase(std::unique(prepared.observations.begin(),
                                          prepared.observations.end(),
                                          [](const auto &lhs, const auto &rhs) {
                                            return lhs.path == rhs.path;
                                          }),
                              prepared.observations.end());
  prepared.inputs.reserve(prepared.observations.size());
  prepared.record = std::make_shared<detail::SnapshotRecord>();
  prepared.record->snapshot = prepared.snapshot;
  prepared.record->profile = profile;
  return prepared;
}

} // namespace

void detail::AcquisitionRequest::check_cancelled() const {
  if (cancellation.stop_requested())
    throw AcquisitionCancelled();
}

// Retry only when validation or publication rejects a generation. Each attempt
// delegates one selected path, keeping retry policy independent of its phases.
SnapshotPtr
SnapshotCache::Impl::acquire(const detail::AcquisitionRequest &request) {
  for (std::size_t attempt = 0; attempt < options.max_acquisition_attempts;
       ++attempt) {
    request.check_cancelled();
    if (auto snapshot = acquire_once(request))
      return snapshot;
  }
  throw std::runtime_error(
      "snapshot inputs changed during every acquisition attempt");
}

// Copy ownership under the short metadata lock; slow work uses these handles
// after unlocking. Joining a flight takes precedence over reserving a new slot.
detail::AcquisitionAttempt
SnapshotCache::Impl::select_attempt(const detail::AcquisitionRequest &request) {
  detail::AcquisitionAttempt attempt;
  std::lock_guard lock(mutex);
  attempt.file = ensure_file_locked(request.path);
  attempt.profile = find_profile_locked(attempt.file, request);
  attempt.epoch = invalidation_epoch;
  if (attempt.profile && attempt.profile->flight) {
    attempt.flight = attempt.profile->flight;
    attempt.kind = detail::AcquisitionKind::Waiter;
  } else if (attempt.profile && !attempt.profile->generations.empty()) {
    attempt.candidate = attempt.profile->generations.back();
    attempt.kind = detail::AcquisitionKind::Candidate;
  } else {
    start_flight_locked(attempt);
  }
  return attempt;
}

SnapshotPtr
SnapshotCache::Impl::acquire_once(const detail::AcquisitionRequest &request) {
  const auto attempt = select_attempt(request);
  switch (attempt.kind) {
  case detail::AcquisitionKind::Candidate:
    return reuse_candidate(request, attempt);
  case detail::AcquisitionKind::Waiter:
    return join_flight(request, attempt);
  case detail::AcquisitionKind::Builder:
    return build_generation(request, attempt);
  }
  throw std::logic_error("unknown acquisition attempt kind");
}

// Validation runs unlocked. Reverse invalidation can retire this record during
// I/O, so recheck its eligibility before touching LRU or returning the owner.
SnapshotPtr SnapshotCache::Impl::reuse_candidate(
    const detail::AcquisitionRequest &request,
    const detail::AcquisitionAttempt &attempt) {
  std::vector<SnapshotPtr> retired;
  const bool valid = validate(*attempt.candidate->snapshot);
  request.check_cancelled();
  std::lock_guard lock(mutex);
  if (valid && attempt.candidate->reusable &&
      same_file_locked(request, attempt)) {
    lru.touch(attempt.candidate);
    return attempt.candidate->snapshot;
  }
  if (!valid)
    retire_locked(attempt.candidate, retired);
  return {};
}

SnapshotPtr
SnapshotCache::Impl::join_flight(const detail::AcquisitionRequest &request,
                                 const detail::AcquisitionAttempt &attempt) {
  WaitingAcquisition waiter(mutex, waiting_acquisitions);
  const auto result = await_flight(attempt.flight, request.cancellation);
  if (result.error)
    std::rethrow_exception(result.error);
  request.check_cancelled();
  if (!result.snapshot)
    return {};

  // A completed generation can already be stale by the time this waiter wakes.
  const bool valid = validate(*result.snapshot);
  request.check_cancelled();
  std::vector<SnapshotPtr> retired;
  std::lock_guard lock(mutex);
  if (valid && result.publication_epoch == invalidation_epoch &&
      same_file_locked(request, attempt))
    return result.snapshot;
  if (!valid)
    retire_snapshot_locked(attempt.profile, result.snapshot, retired);
  return {};
}

SnapshotPtr SnapshotCache::Impl::build_generation(
    const detail::AcquisitionRequest &request,
    const detail::AcquisitionAttempt &attempt) {
  detail::FlightResult result;
  std::vector<SnapshotPtr> retired;
  try {
    auto built = load_snapshot(request, attempt);
    if (validate(*built)) {
      auto prepared = prepare_snapshot(std::move(built), attempt.profile);
      result.snapshot = publish_generation(request, attempt, prepared, retired);
    }
  } catch (...) {
    result.error = std::current_exception();
  }
  // Every leader publishes success, retry, or failure before its own stop token
  // is observed; shared work is never abandoned when that leader cancels.
  finish_flight(attempt, result);
  request.check_cancelled();
  if (result.error)
    std::rethrow_exception(result.error);
  return result.snapshot;
}

// The adapter captures native ownership and complete observations. Reject an
// incomplete main-source manifest before a generation becomes discoverable.
SnapshotPtr
SnapshotCache::Impl::load_snapshot(const detail::AcquisitionRequest &request,
                                   const detail::AcquisitionAttempt &attempt) {
  auto loaded = loader->load(request.path, request.context);
  if (loaded.inputs.size() > options.max_inputs_per_snapshot)
    throw ResourceExhausted();
  if (!std::ranges::any_of(loaded.inputs, [&](const auto &input) {
        return input.path == request.path && input.kind == InputKind::File;
      }))
    throw std::invalid_argument("snapshot manifest lacks main source");
  return std::make_shared<SnapshotEntry>(attempt.generation, request.identity,
                                         std::move(loaded));
}

// Only prepared metadata crosses this lock boundary. A rejected epoch returns
// a retry; the caller retains the prepared native owner until after unlocking.
SnapshotPtr SnapshotCache::Impl::publish_generation(
    const detail::AcquisitionRequest &request,
    const detail::AcquisitionAttempt &attempt,
    detail::PreparedSnapshot &prepared, std::vector<SnapshotPtr> &retired) {
  std::lock_guard lock(mutex);
  if (!can_publish_locked(request, attempt))
    return {};
  register_inputs_locked(prepared);
  retain_generation_locked(attempt.profile, prepared, retired);
  return prepared.snapshot;
}

// Release the pending slot before notifying callers. Never nest the metadata
// and flight locks; waiters copy the result before reacquiring metadata.
void SnapshotCache::Impl::finish_flight(
    const detail::AcquisitionAttempt &attempt,
    const detail::FlightResult &result) {
  {
    std::lock_guard lock(mutex);
    if (attempt.profile && attempt.profile->flight == attempt.flight)
      attempt.profile->flight.reset();
    --pending_builds;
  }
  {
    std::lock_guard lock(attempt.flight->mutex);
    attempt.flight->snapshot = result.snapshot;
    attempt.flight->publication_epoch = attempt.epoch;
    attempt.flight->error = result.error;
    attempt.flight->done = true;
  }
  attempt.flight->ready.notify_all();
}

} // namespace ctk::cache
