#include "ctk/application/resource_manager.hpp"

#include <algorithm>
#include <array>
#include <limits>
#include <map>
#include <mutex>
#include <openssl/rand.h>
#include <thread>
#include <stdexcept>
#include <unordered_map>
#include <utility>

namespace ctk::application {
namespace {
using Code = ctk::clang_layer::MatchCode;
using ctk::match::v1::ResourceScopeInfo;

std::string make_id() {
  std::array<unsigned char, 16> bytes{};
  if (RAND_bytes(bytes.data(), static_cast<int>(bytes.size())) != 1)
    throw std::runtime_error("resource scope identity generation failed");
  bytes[6] = static_cast<unsigned char>((bytes[6] & 0x0f) | 0x40);
  bytes[8] = static_cast<unsigned char>((bytes[8] & 0x3f) | 0x80);
  constexpr char digits[] = "0123456789abcdef";
  std::string id;
  id.reserve(36);
  for (std::size_t i = 0; i < bytes.size(); ++i) {
    if (i == 4 || i == 6 || i == 8 || i == 10)
      id.push_back('-');
    id.push_back(digits[bytes[i] >> 4]);
    id.push_back(digits[bytes[i] & 0x0f]);
  }
  return id;
}

void set_expiry(google::protobuf::Timestamp *timestamp,
                std::chrono::system_clock::time_point point) {
  const auto nanos = std::chrono::duration_cast<std::chrono::nanoseconds>(
                         point.time_since_epoch())
                         .count();
  timestamp->set_seconds(nanos / 1000000000);
  timestamp->set_nanos(static_cast<int>(nanos % 1000000000));
}

std::uint64_t add_saturated(std::uint64_t left, std::uint64_t right) {
  return right > std::numeric_limits<std::uint64_t>::max() - left
             ? std::numeric_limits<std::uint64_t>::max()
             : left + right;
}
} // namespace

struct ResourceManager::Impl {
  struct Cursor {
    std::string input_identity;
    ctk::cache::SnapshotPtr snapshot;
    std::function<bool()> close;
    std::chrono::steady_clock::time_point expires;
    bool file_lease{false};
    std::uint64_t result_bytes{0};
  };
  struct Scope {
    struct NativeClaim {
      std::string input_identity;
      ctk::match::v1::InputDescriptor input;
      ctk::cache::SnapshotPtr snapshot;
      std::vector<std::function<void()>> release_reuse;
    };
    std::string id;
    std::string owner;
    ctk::match::v1::ResourceScopeState state =
        ctk::match::v1::RESOURCE_SCOPE_STATE_OPEN;
    std::map<std::string, std::uint64_t> reservations;
    std::map<std::string, Cursor> cursors;
    std::map<std::string, Cursor> leases;
    std::map<const ctk::cache::SnapshotEntry *, NativeClaim> native;
    std::uint64_t reserved_bytes = 0;
    std::uint64_t admitted_input_count = 0;
    std::uint64_t memory_limit = 0;
    std::uint64_t peak_reserved = 0;
    std::uint64_t peak_accounted = 0;
    std::uint32_t jobs = 1;
    bool transient = false;
    bool expired_requested = false;
    std::size_t active_work = 0;
    bool cleanup_in_progress = false;
    std::chrono::steady_clock::time_point expires;
    std::chrono::steady_clock::time_point terminal_expiry;
    std::chrono::milliseconds ttl{300000};
  };
  struct Pin {
    std::string input_identity;
    ctk::match::v1::InputDescriptor input;
    ctk::cache::SnapshotPtr snapshot;
  };
  struct Work {
    std::string owner;
    std::string scope_id;
    std::map<const ctk::cache::SnapshotEntry *, Pin> snapshots;
  };

  explicit Impl(ResourceManagerSettings config) : settings(config) {
    sweeper = std::thread([this] { sweep_loop(); });
  }

  ~Impl() {
    {
      std::lock_guard guard(mutex);
      stopping = true;
    }
    changed.notify_all();
    if (sweeper.joinable())
      sweeper.join();
  }

  ResourceScopeInfo info(const Scope &scope) const {
    ResourceScopeInfo result;
    result.set_resource_scope_id(scope.id);
    result.set_state(scope.state);
    result.set_admitted_inputs(scope.admitted_input_count);
    result.set_reserved_bytes(scope.reserved_bytes);
    result.set_file_leases(scope.leases.size());
    result.set_result_cursors(scope.cursors.size());
    result.set_active_work(scope.active_work);
    result.set_memory_limit_bytes(scope.memory_limit);
    result.set_jobs(scope.jobs);
    result.set_transient(scope.transient);
    result.set_peak_accounted_bytes(scope.peak_accounted);
    result.set_peak_reserved_bytes(scope.peak_reserved);
    auto accounted = std::uint64_t{0};
    std::map<const ctk::cache::SnapshotEntry *, bool> snapshots;
    for (const auto &[id, cursor] : scope.cursors) {
      (void)id;
      if (cursor.snapshot && snapshots.emplace(cursor.snapshot.get(), true).second)
        accounted = add_saturated(accounted, cursor.snapshot->estimated_bytes);
    }
    for (const auto &[id, lease] : scope.leases) {
      (void)id;
      if (lease.snapshot && snapshots.emplace(lease.snapshot.get(), true).second)
        accounted = add_saturated(accounted, lease.snapshot->estimated_bytes);
    }
    for (const auto &[snapshot, claim] : scope.native) {
      (void)snapshot;
      if (claim.snapshot && snapshots.emplace(claim.snapshot.get(), true).second)
        accounted = add_saturated(accounted, claim.snapshot->estimated_bytes);
    }
    result.set_accounted_native_bytes(accounted);
    for (const auto &[id, cursor] : scope.cursors) {
      (void)id;
      result.set_result_buffer_bytes(add_saturated(
          result.result_buffer_bytes(), cursor.result_bytes));
    }
    const bool terminal =
        scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_RELEASED ||
        scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_EXPIRED;
    const auto now = std::chrono::steady_clock::now();
    const auto expires = terminal ? scope.terminal_expiry : scope.expires;
    set_expiry(result.mutable_expires_at(),
               std::chrono::system_clock::now() +
                   std::chrono::duration_cast<std::chrono::system_clock::duration>(
                       std::max(std::chrono::steady_clock::duration::zero(),
                                expires - now)));
    result.set_cleanup_acknowledged(terminal && scope.active_work == 0 &&
                                    scope.cursors.empty() && scope.leases.empty() &&
                                    scope.native.empty());
    return result;
  }

  std::uint64_t active_reservations() const {
    std::uint64_t bytes = 0;
    for (const auto &[id, scope] : scopes) {
      (void)id;
      if (scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_RELEASED ||
          scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_EXPIRED)
        continue;
      bytes = add_saturated(bytes, scope.reserved_bytes);
    }
    return bytes;
  }

  std::uint64_t active_inputs() const {
    std::map<std::string, bool> inputs;
    for (const auto &[id, scope] : scopes) {
      (void)id;
      if (scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_RELEASED ||
          scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_EXPIRED)
        continue;
      for (const auto &[input, bytes] : scope.reservations) {
        (void)bytes;
        inputs.emplace(input, true);
      }
      for (const auto &[resource_id, resource] : scope.cursors) {
        (void)resource_id;
        inputs.emplace(resource.input_identity, true);
      }
      for (const auto &[resource_id, resource] : scope.leases) {
        (void)resource_id;
        inputs.emplace(resource.input_identity, true);
      }
      for (const auto &[snapshot, claim] : scope.native) {
        (void)snapshot;
        inputs.emplace(claim.input_identity, true);
      }
    }
    for (const auto &[id, resource] : unscoped) {
      (void)id;
      inputs.emplace(resource.input_identity, true);
    }
    for (const auto &[token, work] : works) {
      (void)token;
      for (const auto &[snapshot, identity_and_pin] : work.snapshots) {
        (void)snapshot;
        inputs.emplace(identity_and_pin.input_identity, true);
      }
    }
    return inputs.size();
  }

  bool contains_input(const std::string &identity) const {
    for (const auto &[id, scope] : scopes) {
      (void)id;
      if (scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_RELEASED ||
          scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_EXPIRED)
        continue;
      if (scope.reservations.contains(identity))
        return true;
      for (const auto &[resource_id, resource] : scope.cursors) {
        (void)resource_id;
        if (resource.input_identity == identity)
          return true;
      }
      for (const auto &[resource_id, resource] : scope.leases) {
        (void)resource_id;
        if (resource.input_identity == identity)
          return true;
      }
      for (const auto &[snapshot, claim] : scope.native) {
        (void)snapshot;
        if (claim.input_identity == identity)
          return true;
      }
    }
    for (const auto &[id, resource] : unscoped) {
      (void)id;
      if (resource.input_identity == identity)
        return true;
    }
    for (const auto &[token, work] : works) {
      (void)token;
      for (const auto &[snapshot, identity_and_pin] : work.snapshots) {
        (void)snapshot;
        if (identity_and_pin.input_identity == identity)
          return true;
      }
    }
    return false;
  }

  std::uint64_t active_accounted() const {
    std::map<const ctk::cache::SnapshotEntry *, bool> snapshots;
    std::uint64_t bytes = 0;
    for (const auto &[id, scope] : scopes) {
      (void)id;
      if (scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_RELEASED ||
          scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_EXPIRED)
        continue;
      const auto add = [&](const auto &resources) {
        for (const auto &[resource_id, resource] : resources) {
          (void)resource_id;
          if (resource.snapshot && snapshots.emplace(resource.snapshot.get(), true).second)
            bytes = add_saturated(bytes, resource.snapshot->estimated_bytes);
        }
      };
      add(scope.cursors);
      add(scope.leases);
      for (const auto &[snapshot, claim] : scope.native) {
        (void)snapshot;
        if (claim.snapshot && snapshots.emplace(claim.snapshot.get(), true).second)
          bytes = add_saturated(bytes, claim.snapshot->estimated_bytes);
      }
    }
    for (const auto &[id, resource] : unscoped) {
      (void)id;
      if (resource.snapshot && snapshots.emplace(resource.snapshot.get(), true).second)
        bytes = add_saturated(bytes, resource.snapshot->estimated_bytes);
    }
    for (const auto &[token, work] : works) {
      (void)token;
      for (const auto &[snapshot, identity_and_pin] : work.snapshots) {
        if (identity_and_pin.snapshot && snapshots.emplace(snapshot, true).second)
          bytes = add_saturated(bytes,
                                identity_and_pin.snapshot->estimated_bytes);
      }
    }
    return bytes;
  }

  std::uint64_t active_result_bytes() const {
    std::uint64_t bytes = 0;
    for (const auto &[id, scope] : scopes) {
      (void)id;
      if (scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_RELEASED ||
          scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_EXPIRED)
        continue;
      for (const auto &[resource_id, cursor] : scope.cursors) {
        (void)resource_id;
        bytes = add_saturated(bytes, cursor.result_bytes);
      }
    }
    for (const auto &[id, resource] : unscoped) {
      (void)id;
      bytes = add_saturated(bytes, resource.result_bytes);
    }
    return bytes;
  }

  void collect_finished(std::unique_lock<std::mutex> &lock,
                        std::vector<std::function<bool()>> &callbacks) {
    struct Action {
      std::string scope_id;
      std::string resource_id;
      enum class Kind { Cursor, Lease, Native } kind;
      std::function<bool()> callback;
      bool completed{false};
    };
    std::vector<Action> actions;
    std::vector<std::string> selected_scopes;
    for (auto &[id, scope] : scopes) {
      (void)id;
      if (scope.state != ctk::match::v1::RESOURCE_SCOPE_STATE_RELEASING ||
          scope.active_work != 0 || scope.cleanup_in_progress)
        continue;
      scope.cleanup_in_progress = true;
      selected_scopes.push_back(scope.id);
      for (auto &[cursor_id, cursor] : scope.cursors) {
        actions.push_back({scope.id, cursor_id, Action::Kind::Cursor,
                           cursor.close, false});
      }
      for (auto &[lease_id, lease] : scope.leases) {
        actions.push_back({scope.id, lease_id, Action::Kind::Lease,
                           lease.close, false});
      }
      for (auto &[snapshot, claim] : scope.native) {
        const auto key = std::to_string(reinterpret_cast<std::uintptr_t>(snapshot));
        if (claim.release_reuse.empty()) {
          actions.push_back({scope.id, key, Action::Kind::Native, {}, false});
        } else {
          for (const auto &release : claim.release_reuse) {
            actions.push_back({scope.id, key, Action::Kind::Native,
                               [release] {
                                 release();
                                 return true;
                               }, false});
          }
        }
      }
    }
    lock.unlock();
    for (auto &action : actions) {
      if (!action.callback) {
        action.completed = true;
        continue;
      }
      try {
        action.completed = action.callback();
      } catch (...) {
        action.completed = false;
      }
    }
    lock.lock();
    std::map<std::pair<std::string, std::string>, bool> native_complete;
    for (const auto &action : actions) {
      const auto found = scopes.find(action.scope_id);
      if (found == scopes.end())
        continue;
      auto &scope = found->second;
      if (action.kind == Action::Kind::Cursor && action.completed)
        scope.cursors.erase(action.resource_id);
      else if (action.kind == Action::Kind::Lease && action.completed)
        scope.leases.erase(action.resource_id);
      else if (action.kind == Action::Kind::Native) {
        auto [status, inserted] = native_complete.try_emplace(
            {action.scope_id, action.resource_id}, true);
        (void)inserted;
        status->second = status->second && action.completed;
      }
    }
    for (auto &[identity, complete] : native_complete) {
      if (!complete)
        continue;
      const auto scope = scopes.find(identity.first);
      if (scope == scopes.end())
        continue;
      const auto snapshot = reinterpret_cast<const ctk::cache::SnapshotEntry *>(
          std::stoull(identity.second));
      scope->second.native.erase(snapshot);
    }
    for (const auto &id : selected_scopes) {
      const auto found = scopes.find(id);
      if (found == scopes.end())
        continue;
      auto &scope = found->second;
      if (!scope.cleanup_in_progress)
        continue;
      if (scope.cursors.empty() && scope.leases.empty() && scope.native.empty()) {
        scope.reservations.clear();
        scope.reserved_bytes = 0;
        scope.cleanup_in_progress = false;
        scope.state = scope.expired_requested
                          ? ctk::match::v1::RESOURCE_SCOPE_STATE_EXPIRED
                          : ctk::match::v1::RESOURCE_SCOPE_STATE_RELEASED;
        scope.terminal_expiry = std::chrono::steady_clock::now() +
                                settings.terminal_ttl;
      } else {
        scope.cleanup_in_progress = false;
      }
    }
    callbacks.clear();
    changed.notify_all();
  }

  void sweep_loop() {
    std::unique_lock lock(mutex);
    while (!stopping) {
      changed.wait_for(lock, std::chrono::milliseconds(100),
                       [&] { return stopping; });
      if (stopping)
        break;
      const auto now = std::chrono::steady_clock::now();
      for (auto &[id, scope] : scopes) {
        (void)id;
        if ((scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_OPEN ||
             scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_CANCELLING) &&
            scope.expires <= now) {
          scope.expired_requested = true;
          scope.state = ctk::match::v1::RESOURCE_SCOPE_STATE_RELEASING;
        }
      }
      std::vector<std::string> expired_resources;
      for (const auto &[id, resource] : unscoped)
        if (resource.expires <= now)
          expired_resources.push_back(id);
      std::vector<std::function<bool()>> callbacks;
      collect_finished(lock, callbacks);
      for (const auto &id : expired_resources) {
        auto found = unscoped.find(id);
        if (found == unscoped.end())
          continue;
        const auto close = found->second.close;
        lock.unlock();
        bool closed = false;
        try {
          closed = !close || close();
        } catch (...) {
        }
        lock.lock();
        found = unscoped.find(id);
        if (closed && found != unscoped.end())
          unscoped.erase(found);
      }
      std::erase_if(scopes, [&](const auto &entry) {
        const auto &scope = entry.second;
        return (scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_RELEASED ||
                scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_EXPIRED) &&
               scope.terminal_expiry <= now;
      });
    }
  }

  void release_all() {
    std::vector<std::function<bool()>> callbacks;
    for (auto &[id, scope] : scopes) {
      (void)id;
      for (auto &[cursor_id, cursor] : scope.cursors) {
        (void)cursor_id;
        if (cursor.close)
          callbacks.push_back(std::move(cursor.close));
      }
      for (auto &[lease_id, lease] : scope.leases) {
        (void)lease_id;
        if (lease.close)
          callbacks.push_back(std::move(lease.close));
      }
    }
    for (auto &callback : callbacks) {
      try {
        (void)callback();
      } catch (...) {
      }
    }
  }

  ResourceManagerSettings settings;
  mutable std::mutex mutex;
  std::condition_variable changed;
  std::map<std::string, Scope> scopes;
  std::map<std::string, Cursor> unscoped;
  std::map<std::string, Work> works;
  std::thread sweeper;
  bool stopping = false;
};

ResourceManager::WorkLease::WorkLease(std::shared_ptr<ResourceManager> manager,
                                      std::string id, std::string owner)
    : manager_(std::move(manager)), id_(std::move(id)),
      owner_(std::move(owner)) {}
ResourceManager::WorkLease::WorkLease(WorkLease &&other) noexcept
    : manager_(std::move(other.manager_)), id_(std::move(other.id_)),
      owner_(std::move(other.owner_)) {}
ResourceManager::WorkLease &
ResourceManager::WorkLease::operator=(WorkLease &&other) noexcept {
  if (this != &other) {
    reset();
    manager_ = std::move(other.manager_);
    id_ = std::move(other.id_);
    owner_ = std::move(other.owner_);
  }
  return *this;
}
ResourceManager::WorkLease::~WorkLease() { reset(); }
void ResourceManager::WorkLease::reset() noexcept {
  if (manager_)
    manager_->finish_work(owner_, id_);
  manager_.reset();
}
bool ResourceManager::WorkLease::checkpoint() const {
  return !manager_ || manager_->checkpoint(owner_, id_);
}

ResourceManager::ResourceManager(ResourceManagerSettings settings)
    : impl_(std::make_unique<Impl>(settings)) {
  if (!settings.max_inputs || !settings.max_memory_bytes ||
      !settings.max_jobs || !settings.max_scopes ||
      settings.default_ttl.count() <= 0 || settings.terminal_ttl.count() <= 0)
    throw std::invalid_argument("resource scope limits must be positive");
}
ResourceManager::~ResourceManager() = default;

Code ResourceManager::open_scope(
    const std::string &owner,
    const ctk::match::v1::OpenResourceScopeRequest &request,
    const std::vector<ResourceInputReservation> &inputs,
    ResourceScopeInfo &response, std::string &message) {
  if (owner.empty()) {
    message = "caller owner is required";
    return Code::InvalidArgument;
  }
  if (inputs.size() != static_cast<std::size_t>(request.inputs_size())) {
    message = "resource scope input resolution is incomplete";
    return Code::InvalidArgument;
  }
  const auto jobs = request.has_jobs() ? request.jobs() : 1;
  if (!jobs) {
    message = "jobs must be positive";
    return Code::InvalidArgument;
  }
  const auto ttl = request.has_ttl_ms()
                       ? std::chrono::milliseconds(request.ttl_ms())
                       : impl_->settings.default_ttl;
  if (ttl.count() <= 0 || ttl > impl_->settings.default_ttl) {
    message = "resource scope ttl must be positive and within the server limit";
    return Code::InvalidArgument;
  }
  std::map<std::string, std::uint64_t> reservations;
  std::uint64_t estimated = 0;
  for (const auto &input : inputs) {
    if (input.identity.empty()) {
      message = "resource scope input identity is empty";
      return Code::InvalidArgument;
    }
    const auto [found, inserted] =
        reservations.emplace(input.identity, input.estimated_bytes);
    if (!inserted)
      found->second = std::max(found->second, input.estimated_bytes);
  }
  for (const auto &[identity, bytes] : reservations) {
    (void)identity;
    estimated = add_saturated(estimated, bytes);
  }
  const auto lower_limit = request.has_memory_bytes()
                               ? request.memory_bytes()
                               : impl_->settings.max_memory_bytes;
  if (!lower_limit || lower_limit > impl_->settings.max_memory_bytes ||
      estimated > lower_limit) {
    message = "resource scope exceeds its memory admission limit";
    return Code::ResourceExhausted;
  }
  std::lock_guard guard(impl_->mutex);
  std::erase_if(impl_->scopes, [&](const auto &entry) {
    const auto &scope = entry.second;
    return (scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_RELEASED ||
            scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_EXPIRED) &&
           scope.terminal_expiry <= std::chrono::steady_clock::now();
  });
  const auto active_scope_count = std::count_if(
      impl_->scopes.begin(), impl_->scopes.end(), [](const auto &entry) {
        return entry.second.state !=
                   ctk::match::v1::RESOURCE_SCOPE_STATE_RELEASED &&
               entry.second.state !=
                   ctk::match::v1::RESOURCE_SCOPE_STATE_EXPIRED;
      });
  if (active_scope_count >= impl_->settings.max_scopes) {
    message = "resource scope count limit exceeded";
    return Code::ResourceExhausted;
  }
  auto projected_inputs = impl_->active_inputs();
  for (const auto &[identity, bytes] : reservations) {
    (void)bytes;
    if (!impl_->contains_input(identity))
      projected_inputs = add_saturated(projected_inputs, 1);
  }
  const auto projected_bytes = add_saturated(
      add_saturated(add_saturated(impl_->active_reservations(),
                                  impl_->active_accounted()),
                    impl_->active_result_bytes()),
      estimated);
  if (projected_inputs > impl_->settings.max_inputs ||
      projected_bytes > impl_->settings.max_memory_bytes) {
    message = "resource scope admission limits exceeded";
    return Code::ResourceExhausted;
  }
  Impl::Scope scope;
  scope.id = make_id();
  scope.owner = owner;
  scope.reservations = std::move(reservations);
  scope.admitted_input_count = scope.reservations.size();
  scope.reserved_bytes = estimated;
  scope.memory_limit = lower_limit;
  scope.peak_reserved = estimated;
  scope.jobs = jobs;
  scope.transient = request.transient();
  scope.expires = std::chrono::steady_clock::now() + ttl;
  scope.ttl = ttl;
  auto [entry, inserted] = impl_->scopes.emplace(scope.id, std::move(scope));
  if (!inserted) {
    message = "resource scope identity collision";
    return Code::Internal;
  }
  const auto tombstone_cap = impl_->settings.max_scopes * 4;
  std::vector<std::pair<std::chrono::steady_clock::time_point, std::string>>
      tombstones;
  for (const auto &[id, existing] : impl_->scopes)
    if (existing.state == ctk::match::v1::RESOURCE_SCOPE_STATE_RELEASED ||
        existing.state == ctk::match::v1::RESOURCE_SCOPE_STATE_EXPIRED)
      tombstones.emplace_back(existing.terminal_expiry, id);
  if (tombstones.size() > tombstone_cap) {
    std::sort(tombstones.begin(), tombstones.end());
    for (std::size_t i = 0; i < tombstones.size() - tombstone_cap; ++i)
      impl_->scopes.erase(tombstones[i].second);
  }
  response = impl_->info(entry->second);
  impl_->changed.notify_all();
  return Code::Ok;
}

Code ResourceManager::begin_work(const std::string &owner,
                                 const std::string &scope_id, WorkLease &lease,
                                 std::string &message) {
  if (scope_id.empty()) {
    std::lock_guard guard(impl_->mutex);
    const auto work_id = make_id();
    impl_->works.emplace(work_id, Impl::Work{owner, {}, {}});
    lease = WorkLease(shared_from_this(), work_id, owner);
    return Code::Ok;
  }
  std::lock_guard guard(impl_->mutex);
  const auto found = impl_->scopes.find(scope_id);
  if (found == impl_->scopes.end() || found->second.owner != owner) {
    message = "resource scope unavailable";
    return Code::NotFound;
  }
  auto &scope = found->second;
  if (scope.state != ctk::match::v1::RESOURCE_SCOPE_STATE_OPEN ||
      scope.expires <= std::chrono::steady_clock::now()) {
    message = "resource scope is not open";
    return Code::FailedPrecondition;
  }
  if (scope.active_work >= scope.jobs) {
    message = "resource scope job limit is occupied";
    return Code::ResourceExhausted;
  }
  ++scope.active_work;
  scope.expires = std::chrono::steady_clock::now() + scope.ttl;
  const auto work_id = make_id();
  impl_->works.emplace(work_id, Impl::Work{owner, scope_id, {}});
  lease = WorkLease(shared_from_this(), work_id, owner);
  return Code::Ok;
}

bool ResourceManager::scope_transient(const std::string &owner,
                                      const std::string &scope_id) const {
  if (scope_id.empty())
    return false;
  std::lock_guard guard(impl_->mutex);
  const auto found = impl_->scopes.find(scope_id);
  return found != impl_->scopes.end() && found->second.owner == owner &&
         found->second.transient;
}

Code ResourceManager::describe_scope(const std::string &owner,
                                     const std::string &scope_id,
                                     ResourceScopeInfo &response) {
  std::lock_guard guard(impl_->mutex);
  const auto found = impl_->scopes.find(scope_id);
  if (found == impl_->scopes.end() || found->second.owner != owner)
    return Code::NotFound;
  response = impl_->info(found->second);
  return Code::Ok;
}

Code ResourceManager::cancel_scope(const std::string &owner,
                                   const std::string &scope_id,
                                   ResourceScopeInfo &response) {
  std::lock_guard guard(impl_->mutex);
  const auto found = impl_->scopes.find(scope_id);
  if (found == impl_->scopes.end() || found->second.owner != owner)
    return Code::NotFound;
  auto &scope = found->second;
  if (scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_OPEN)
    scope.state = ctk::match::v1::RESOURCE_SCOPE_STATE_CANCELLING;
  response = impl_->info(scope);
  impl_->changed.notify_all();
  return Code::Ok;
}

Code ResourceManager::release_scope(const std::string &owner,
                                    const std::string &scope_id,
                                    ResourceScopeInfo &response) {
  std::vector<std::function<bool()>> callbacks;
  std::unique_lock lock(impl_->mutex);
  auto found = impl_->scopes.find(scope_id);
  if (found == impl_->scopes.end() || found->second.owner != owner)
    return Code::NotFound;
  auto &scope = found->second;
  if (scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_RELEASED ||
      scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_EXPIRED) {
    response = impl_->info(scope);
    return Code::Ok;
  }
  scope.state = ctk::match::v1::RESOURCE_SCOPE_STATE_RELEASING;
  impl_->changed.notify_all();
  impl_->changed.wait(lock, [&] {
    const auto current = impl_->scopes.find(scope_id);
    return current == impl_->scopes.end() ||
           current->second.state ==
               ctk::match::v1::RESOURCE_SCOPE_STATE_RELEASED ||
           current->second.state ==
               ctk::match::v1::RESOURCE_SCOPE_STATE_EXPIRED ||
           (current->second.active_work == 0 &&
            !current->second.cleanup_in_progress);
  });
  found = impl_->scopes.find(scope_id);
  if (found == impl_->scopes.end())
    return Code::NotFound;
  impl_->collect_finished(lock, callbacks);
  found = impl_->scopes.find(scope_id);
  if (found == impl_->scopes.end())
    return Code::NotFound;
  response = impl_->info(found->second);
  return Code::Ok;
}

void ResourceManager::register_cursor(const std::string &owner,
                                     const std::string &scope_id,
                                     const std::string &cursor_id,
                                     const std::string &input_identity,
                                     ctk::cache::SnapshotPtr snapshot,
                                     std::function<bool()> close,
                                     std::uint64_t result_bytes) {
  std::lock_guard guard(impl_->mutex);
  if (scope_id.empty()) {
    const bool new_input = !impl_->contains_input(input_identity);
    if (new_input && impl_->active_inputs() >= impl_->settings.max_inputs)
      throw std::runtime_error("server input limit exceeded");
    const auto key = owner + ":" + cursor_id;
    const auto [entry, inserted] = impl_->unscoped.insert_or_assign(
        key,
        Impl::Cursor{input_identity, std::move(snapshot), std::move(close),
                     std::chrono::steady_clock::now() +
                         impl_->settings.default_ttl, false, result_bytes});
    (void)inserted;
    if (add_saturated(impl_->active_reservations(),
                      add_saturated(impl_->active_accounted(),
                                    impl_->active_result_bytes())) >
        impl_->settings.max_memory_bytes) {
      impl_->unscoped.erase(entry);
      throw std::runtime_error("server native estimate exceeds its limit");
    }
    return;
  }
  const auto found = impl_->scopes.find(scope_id);
  if (found == impl_->scopes.end() || found->second.owner != owner ||
      found->second.state != ctk::match::v1::RESOURCE_SCOPE_STATE_OPEN)
    throw std::runtime_error("resource scope closed before cursor publication");
  auto &scope = found->second;
  const auto belongs = [&] {
    if (scope.reservations.contains(input_identity))
      return true;
    for (const auto &[id, resource] : scope.cursors) {
      (void)id;
      if (resource.input_identity == input_identity)
        return true;
    }
    for (const auto &[id, resource] : scope.leases) {
      (void)id;
      if (resource.input_identity == input_identity)
        return true;
    }
    for (const auto &[snapshot_id, resource] : scope.native) {
      (void)snapshot_id;
      if (resource.input_identity == input_identity)
        return true;
    }
    return false;
  };
  if (!belongs())
    throw std::runtime_error("input is outside the resource scope manifest");
  scope.cursors.insert_or_assign(
      cursor_id, Impl::Cursor{input_identity, std::move(snapshot),
                              std::move(close),
                              std::chrono::steady_clock::now() +
                                  impl_->settings.default_ttl, false,
                              result_bytes});
  std::uint64_t bytes = 0;
  std::map<const ctk::cache::SnapshotEntry *, bool> unique;
  for (const auto &[id, cursor] : scope.cursors) {
    (void)id;
    if (cursor.snapshot && unique.emplace(cursor.snapshot.get(), true).second)
      bytes = add_saturated(bytes, cursor.snapshot->estimated_bytes);
  }
  std::uint64_t buffers = 0;
  for (const auto &[id, cursor] : scope.cursors) {
    (void)id;
    buffers = add_saturated(buffers, cursor.result_bytes);
  }
  const auto reservation = scope.reservations.find(input_identity);
  const auto pending_scope = scope.reserved_bytes -
      (reservation != scope.reservations.end() ? reservation->second : 0);
  const auto scope_projected = add_saturated(
      add_saturated(impl_->info(scope).accounted_native_bytes(), buffers),
      pending_scope);
  if (scope_projected > scope.memory_limit) {
    auto it = scope.cursors.find(cursor_id);
    scope.cursors.erase(it);
    throw std::runtime_error("resource scope native estimate exceeds its limit");
  }
  auto pending_bytes = impl_->active_reservations();
  if (reservation != scope.reservations.end())
    pending_bytes -= reservation->second;
  std::uint64_t global = add_saturated(pending_bytes,
                                       impl_->active_accounted());
  global = add_saturated(global, impl_->active_result_bytes());
  if (global > impl_->settings.max_memory_bytes) {
    scope.cursors.erase(cursor_id);
    throw std::runtime_error("server native estimate exceeds its limit");
  }
  scope.peak_accounted = std::max(scope.peak_accounted, bytes);
  if (reservation != scope.reservations.end()) {
    scope.reserved_bytes -= reservation->second;
    scope.reservations.erase(reservation);
  }
}

void ResourceManager::register_file_lease(
    const std::string &owner, const std::string &scope_id,
    const std::string &lease_id, const std::string &input_identity,
    ctk::cache::SnapshotPtr snapshot,
    std::function<bool()> close) {
  std::lock_guard guard(impl_->mutex);
  if (scope_id.empty()) {
    const bool new_input = !impl_->contains_input(input_identity);
    if (new_input && impl_->active_inputs() >= impl_->settings.max_inputs)
      throw std::runtime_error("server input limit exceeded");
    const auto key = owner + ":" + lease_id;
    const auto [entry, inserted] = impl_->unscoped.insert_or_assign(
        key,
        Impl::Cursor{input_identity, std::move(snapshot), std::move(close),
                     std::chrono::steady_clock::now() +
                         impl_->settings.default_ttl, true});
    (void)inserted;
    if (add_saturated(impl_->active_reservations(),
                      add_saturated(impl_->active_accounted(),
                                    impl_->active_result_bytes())) >
        impl_->settings.max_memory_bytes) {
      impl_->unscoped.erase(entry);
      throw std::runtime_error("server native estimate exceeds its limit");
    }
    return;
  }
  const auto found = impl_->scopes.find(scope_id);
  if (found == impl_->scopes.end() || found->second.owner != owner ||
      found->second.state != ctk::match::v1::RESOURCE_SCOPE_STATE_OPEN)
    throw std::runtime_error("resource scope closed before lease publication");
  auto &scope = found->second;
  const auto belongs = [&] {
    if (scope.reservations.contains(input_identity))
      return true;
    for (const auto &[id, resource] : scope.cursors) {
      (void)id;
      if (resource.input_identity == input_identity)
        return true;
    }
    for (const auto &[id, resource] : scope.leases) {
      (void)id;
      if (resource.input_identity == input_identity)
        return true;
    }
    for (const auto &[snapshot_id, resource] : scope.native) {
      (void)snapshot_id;
      if (resource.input_identity == input_identity)
        return true;
    }
    return false;
  };
  if (!belongs())
    throw std::runtime_error("input is outside the resource scope manifest");
  found->second.leases.insert_or_assign(
      lease_id, Impl::Cursor{input_identity, std::move(snapshot),
                             std::move(close),
                             std::chrono::steady_clock::now() +
                                 impl_->settings.default_ttl});
  const auto reservation = scope.reservations.find(input_identity);
  const auto scope_info = impl_->info(scope);
  const auto pending_scope = scope.reserved_bytes -
      (reservation != scope.reservations.end() ? reservation->second : 0);
  auto pending_bytes = impl_->active_reservations();
  if (reservation != scope.reservations.end())
    pending_bytes -= reservation->second;
  const auto global = add_saturated(
      add_saturated(pending_bytes, impl_->active_accounted()),
      impl_->active_result_bytes());
  if (global > impl_->settings.max_memory_bytes ||
      add_saturated(add_saturated(scope_info.accounted_native_bytes(),
                                  scope_info.result_buffer_bytes()),
                    pending_scope) > scope.memory_limit) {
    found->second.leases.erase(lease_id);
    throw std::runtime_error("server native estimate exceeds its limit");
  }
  if (reservation != scope.reservations.end()) {
    scope.reserved_bytes -= reservation->second;
    scope.reservations.erase(reservation);
  }
}

void ResourceManager::claim_snapshot(
    const std::string &owner, const std::string &scope_id,
    const std::string &input_identity, ctk::cache::SnapshotPtr snapshot,
    std::function<void()> release_reuse,
    ctk::match::v1::InputDescriptor input) {
  if (scope_id.empty())
    return;
  std::lock_guard guard(impl_->mutex);
  const auto found = impl_->scopes.find(scope_id);
  if (found == impl_->scopes.end() || found->second.owner != owner ||
      (found->second.state != ctk::match::v1::RESOURCE_SCOPE_STATE_OPEN &&
       found->second.state != ctk::match::v1::RESOURCE_SCOPE_STATE_CANCELLING)) {
    if (release_reuse)
      release_reuse();
    throw std::runtime_error("resource scope closed during native acquisition");
  }
  auto &scope = found->second;
  bool member = scope.reservations.contains(input_identity);
  for (const auto &[id, resource] : scope.cursors) {
    (void)id;
    member = member || resource.input_identity == input_identity;
  }
  for (const auto &[id, resource] : scope.leases) {
    (void)id;
    member = member || resource.input_identity == input_identity;
  }
  for (const auto &[identity, claim] : scope.native) {
    (void)identity;
    member = member || claim.input_identity == input_identity;
  }
  if (!member) {
    if (release_reuse)
      release_reuse();
    throw std::runtime_error("input is outside the resource scope manifest");
  }
  auto &claim = scope.native[snapshot.get()];
  if (!claim.snapshot) {
    claim.input_identity = input_identity;
    claim.input = std::move(input);
    claim.snapshot = snapshot;
  }
  if (release_reuse)
    claim.release_reuse.push_back(std::move(release_reuse));

  const auto scope_info = impl_->info(scope);
  const auto reservation = scope.reservations.find(input_identity);
  auto pending_bytes = impl_->active_reservations();
  if (reservation != scope.reservations.end())
    pending_bytes -= reservation->second;
  const auto global = add_saturated(pending_bytes, impl_->active_accounted());
  const auto global_with_results =
      add_saturated(global, impl_->active_result_bytes());
  const auto pending_scope = scope.reserved_bytes -
      (reservation != scope.reservations.end() ? reservation->second : 0);
  const auto scope_projected = add_saturated(
      add_saturated(scope_info.accounted_native_bytes(),
                    scope_info.result_buffer_bytes()),
      pending_scope);
  if (scope_projected > scope.memory_limit ||
      global_with_results > impl_->settings.max_memory_bytes) {
    if (!claim.release_reuse.empty()) {
      auto release = std::move(claim.release_reuse.back());
      claim.release_reuse.pop_back();
      if (release)
        release();
    }
    if (claim.release_reuse.empty() &&
        (!claim.snapshot || claim.snapshot.use_count() <= 2))
      scope.native.erase(snapshot.get());
    throw std::runtime_error("native snapshot estimate exceeds admission limit");
  }
  scope.peak_accounted = std::max(scope.peak_accounted,
                                  scope_info.accounted_native_bytes());
  if (reservation != scope.reservations.end()) {
    scope.reserved_bytes -= reservation->second;
    scope.reservations.erase(reservation);
  }
}

void ResourceManager::unregister_cursor(const std::string &scope_id,
                                        const std::string &cursor_id) {
  std::lock_guard guard(impl_->mutex);
  if (scope_id.empty()) {
    for (auto it = impl_->unscoped.begin(); it != impl_->unscoped.end();) {
      if (it->first.ends_with(":" + cursor_id))
        it = impl_->unscoped.erase(it);
      else
        ++it;
    }
    return;
  }
  const auto found = impl_->scopes.find(scope_id);
  if (found != impl_->scopes.end())
    found->second.cursors.erase(cursor_id);
  impl_->changed.notify_all();
}

void ResourceManager::touch_cursor(const std::string &scope_id,
                                   const std::string &cursor_id,
                                   std::uint64_t result_bytes) {
  std::lock_guard guard(impl_->mutex);
  const auto expires = std::chrono::steady_clock::now() +
                       impl_->settings.default_ttl;
  if (scope_id.empty()) {
    for (auto &[id, resource] : impl_->unscoped) {
      if (id.ends_with(":" + cursor_id)) {
        resource.expires = expires;
        resource.result_bytes = result_bytes;
      }
    }
  } else if (const auto scope = impl_->scopes.find(scope_id);
             scope != impl_->scopes.end()) {
    if (const auto cursor = scope->second.cursors.find(cursor_id);
        cursor != scope->second.cursors.end()) {
      cursor->second.expires = expires;
      cursor->second.result_bytes = result_bytes;
    }
  }
  impl_->changed.notify_all();
}

void ResourceManager::unregister_file_lease(const std::string &scope_id,
                                             const std::string &lease_id) {
  std::lock_guard guard(impl_->mutex);
  if (scope_id.empty()) {
    for (auto it = impl_->unscoped.begin(); it != impl_->unscoped.end();) {
      if (it->first.ends_with(":" + lease_id))
        it = impl_->unscoped.erase(it);
      else
        ++it;
    }
    return;
  }
  const auto found = impl_->scopes.find(scope_id);
  if (found != impl_->scopes.end())
    found->second.leases.erase(lease_id);
  impl_->changed.notify_all();
}

void ResourceManager::register_work_snapshot(
    const std::string &owner, const std::string &work_token,
    const std::string &input_identity, ctk::cache::SnapshotPtr snapshot,
    ctk::match::v1::InputDescriptor input) {
  if (!snapshot)
    return;
  std::lock_guard guard(impl_->mutex);
  const auto work = impl_->works.find(work_token);
  if (work == impl_->works.end() || work->second.owner != owner)
    throw std::runtime_error("native work lease expired before acquisition");
  const auto new_input = !impl_->contains_input(input_identity);
  if (new_input && impl_->active_inputs() >= impl_->settings.max_inputs)
    throw std::runtime_error("server input limit exceeded");
  const auto [pin, inserted] = work->second.snapshots.try_emplace(
      snapshot.get(), Impl::Pin{input_identity, std::move(input),
                                std::move(snapshot)});
  (void)pin;
  if (inserted && add_saturated(
                      add_saturated(impl_->active_reservations(),
                                    impl_->active_accounted()),
                      impl_->active_result_bytes()) >
                      impl_->settings.max_memory_bytes) {
    work->second.snapshots.erase(pin);
    throw std::runtime_error("server native estimate exceeds its limit");
  }
}

std::uint64_t ResourceManager::active_work_for(
    const std::string &owner, const std::string &input_identity) const {
  std::lock_guard guard(impl_->mutex);
  std::uint64_t count = 0;
  for (const auto &[token, work] : impl_->works) {
    (void)token;
    if (work.owner != owner)
      continue;
    if (std::any_of(work.snapshots.begin(), work.snapshots.end(),
                    [&](const auto &entry) {
                      return entry.second.input_identity == input_identity;
                    }))
      ++count;
  }
  return count;
}

std::vector<ResourceInputPin>
ResourceManager::input_pins(const std::string &owner) const {
  using Key = std::pair<std::string, const ctk::cache::SnapshotEntry *>;
  std::lock_guard guard(impl_->mutex);
  std::map<Key, ResourceInputPin> pins;
  for (const auto &[scope_id, scope] : impl_->scopes) {
    if (scope.owner != owner)
      continue;
    for (const auto &[snapshot, claim] : scope.native) {
      if (!claim.snapshot)
        continue;
      auto &pin = pins[{claim.input_identity, snapshot}];
      pin.input_identity = claim.input_identity;
      pin.resource_scope_id = scope_id;
      pin.input.CopyFrom(claim.input);
      pin.snapshot = claim.snapshot;
    }
  }
  for (const auto &[token, work] : impl_->works) {
    (void)token;
    if (work.owner != owner)
      continue;
    for (const auto &[snapshot, active] : work.snapshots) {
      if (!active.snapshot)
        continue;
      auto &pin = pins[{active.input_identity, snapshot}];
      pin.input_identity = active.input_identity;
      if (pin.resource_scope_id.empty())
        pin.resource_scope_id = work.scope_id;
      if (pin.input.file_path().empty())
        pin.input.CopyFrom(active.input);
      pin.snapshot = active.snapshot;
      ++pin.active_work;
    }
  }
  std::vector<ResourceInputPin> result;
  result.reserve(pins.size());
  for (auto &[key, pin] : pins) {
    (void)key;
    result.push_back(std::move(pin));
  }
  return result;
}

ctk::match::v1::ResourceStatusResponse ResourceManager::status(
    const ctk::match::v1::CacheResources &cache,
    std::optional<std::uint64_t> resident_bytes) const {
  ctk::match::v1::ResourceStatusResponse result;
  result.set_reusable_snapshots(cache.reusable_snapshots());
  result.set_reusable_memory_bytes(cache.reusable_memory_bytes());
  if (resident_bytes)
    result.set_resident_memory_bytes(*resident_bytes);
  result.set_max_inputs(impl_->settings.max_inputs);
  result.set_max_memory_bytes(impl_->settings.max_memory_bytes);
  result.set_legacy_accounting_separate(true);
  std::lock_guard guard(impl_->mutex);
  std::uint64_t reserved = 0;
  std::uint64_t accounted = 0;
  std::uint64_t work = 0;
  std::uint64_t leases = 0;
  std::uint64_t cursors = 0;
  std::uint64_t result_bytes = 0;
  std::map<std::string, bool> inputs;
  std::map<const ctk::cache::SnapshotEntry *, bool> snapshots;
  for (const auto &[id, scope] : impl_->scopes) {
    (void)id;
    if (scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_OPEN ||
        scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_CANCELLING ||
        scope.state == ctk::match::v1::RESOURCE_SCOPE_STATE_RELEASING) {
      for (const auto &[input, bytes] : scope.reservations) {
        (void)bytes;
        inputs.emplace(input, true);
      }
      reserved = add_saturated(reserved, scope.reserved_bytes);
      work = add_saturated(work, scope.active_work);
      cursors = add_saturated(cursors, scope.cursors.size());
      leases = add_saturated(leases, scope.leases.size());
      for (const auto &[resource_id, cursor] : scope.cursors) {
        (void)resource_id;
        inputs.emplace(cursor.input_identity, true);
        result_bytes = add_saturated(result_bytes, cursor.result_bytes);
        if (cursor.snapshot && snapshots.emplace(cursor.snapshot.get(), true).second)
          accounted = add_saturated(accounted,
                                    cursor.snapshot->estimated_bytes);
      }
      for (const auto &[resource_id, lease] : scope.leases) {
        (void)resource_id;
        inputs.emplace(lease.input_identity, true);
        if (lease.snapshot && snapshots.emplace(lease.snapshot.get(), true).second)
          accounted = add_saturated(accounted,
                                    lease.snapshot->estimated_bytes);
      }
      for (const auto &[snapshot, claim] : scope.native) {
        (void)snapshot;
        inputs.emplace(claim.input_identity, true);
        if (claim.snapshot && snapshots.emplace(claim.snapshot.get(), true).second)
          accounted = add_saturated(accounted,
                                    claim.snapshot->estimated_bytes);
      }
    }
    result.add_scopes()->CopyFrom(impl_->info(scope));
  }
  for (const auto &[id, resource] : impl_->unscoped) {
    (void)id;
    inputs.emplace(resource.input_identity, true);
    if (resource.file_lease)
      leases = add_saturated(leases, 1);
    else {
      cursors = add_saturated(cursors, 1);
      result_bytes = add_saturated(result_bytes, resource.result_bytes);
    }
    if (resource.snapshot && snapshots.emplace(resource.snapshot.get(), true).second)
      accounted = add_saturated(accounted, resource.snapshot->estimated_bytes);
  }
  for (const auto &[token, active] : impl_->works) {
    (void)token;
    for (const auto &[snapshot, pin] : active.snapshots) {
      inputs.emplace(pin.input_identity, true);
      if (pin.snapshot && snapshots.emplace(snapshot, true).second)
        accounted = add_saturated(
            accounted, pin.snapshot->estimated_bytes);
    }
  }
  work = impl_->works.size();
  result.set_opened_inputs(inputs.size());
  result.set_result_cursors(cursors);
  result.set_active_work(work);
  result.set_reserved_bytes(reserved);
  result.set_accounted_native_bytes(accounted);
  result.set_result_buffer_bytes(result_bytes);
  result.set_explicit_file_leases(leases);
  return result;
}

void ResourceManager::finish_work(const std::string &owner,
                                  const std::string &work_token) noexcept {
  std::vector<std::function<bool()>> callbacks;
  std::unique_lock lock(impl_->mutex);
  const auto work = impl_->works.find(work_token);
  if (work == impl_->works.end() || work->second.owner != owner)
    return;
  const auto scope_id = work->second.scope_id;
  impl_->works.erase(work);
  if (scope_id.empty()) {
    impl_->changed.notify_all();
    return;
  }
  const auto found = impl_->scopes.find(scope_id);
  if (found != impl_->scopes.end() && found->second.owner == owner &&
      found->second.active_work)
    --found->second.active_work;
  impl_->changed.notify_all();
  impl_->collect_finished(lock, callbacks);
}

bool ResourceManager::checkpoint(const std::string &owner,
                                 const std::string &work_token) const {
  std::lock_guard guard(impl_->mutex);
  const auto work = impl_->works.find(work_token);
  if (work == impl_->works.end() || work->second.owner != owner)
    return false;
  const auto &scope_id = work->second.scope_id;
  if (scope_id.empty())
    return true;
  const auto found = impl_->scopes.find(scope_id);
  return found != impl_->scopes.end() && found->second.owner == owner &&
         found->second.state == ctk::match::v1::RESOURCE_SCOPE_STATE_OPEN;
}

} // namespace ctk::application
