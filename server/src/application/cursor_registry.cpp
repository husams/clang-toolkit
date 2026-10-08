#include "cursor_registry.hpp"
#include <array>
#include <limits>
#include <openssl/rand.h>
#include <stdexcept>
#include <unordered_set>

namespace ctk::application::detail {
using ctk::clang_layer::MatchCode;
namespace {
std::string new_id() {
  std::array<unsigned char, 16> bytes{};
  if (RAND_bytes(bytes.data(), bytes.size()) != 1)
    throw std::runtime_error("cursor identity generation failed");
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  constexpr char hex[] = "0123456789abcdef";
  std::string id;
  for (std::size_t i = 0; i < bytes.size(); ++i) {
    if (i == 4 || i == 6 || i == 8 || i == 10)
      id += '-';
    id += hex[bytes[i] >> 4];
    id += hex[bytes[i] & 15];
  }
  return id;
}
MatchReply failure(MatchCode code, std::string message) {
  return {code, std::move(message), {}};
}
} // namespace

bool CursorRegistry::valid_id(const std::string &id) {
  if (id.size() != 36 || id[14] != '4' ||
      (id[19] != '8' && id[19] != '9' && id[19] != 'a' && id[19] != 'b'))
    return false;
  for (std::size_t i = 0; i < id.size(); ++i) {
    if (i == 8 || i == 13 || i == 18 || i == 23) {
      if (id[i] != '-')
        return false;
    } else if (!((id[i] >= '0' && id[i] <= '9') ||
                 (id[i] >= 'a' && id[i] <= 'f')))
      return false;
  }
  return true;
}

void CursorRegistry::prune() {
  // try_lock avoids blocking another cursor's operation under the registry
  // lock.
  std::vector<Entry> retired;
  std::lock_guard guard(mutex_);
  for (auto it = cursors_.begin(); it != cursors_.end();) {
    auto &cursor = *it->second.cursor;
    std::unique_lock operation(cursor.operation, std::try_to_lock);
    if (operation && cursor.deadline <= std::chrono::steady_clock::now()) {
      cursor.closed = true;
      retired.push_back(std::move(it->second));
      it = cursors_.erase(it);
    } else {
      ++it;
    }
  }
}

std::shared_ptr<ResultCursor> CursorRegistry::find(const std::string &owner,
                                                   const std::string &id) {
  prune();
  std::lock_guard guard(mutex_);
  const auto found = cursors_.find(id);
  return found == cursors_.end() || found->second.cursor->owner != owner
             ? nullptr
             : found->second.cursor;
}

bool CursorRegistry::fits(const std::string &replacing,
                          const Entry &candidate) const {
  std::unordered_set<const ctk::cache::SnapshotEntry *> snapshots;
  std::uint64_t bytes = 0;
  const auto add = [&](const Entry &entry) {
    if (entry.binding_bytes > settings_.max_memory_bytes - bytes)
      return false;
    bytes += entry.binding_bytes;
    if (entry.snapshot && snapshots.insert(entry.snapshot.get()).second) {
      if (entry.snapshot->estimated_bytes > settings_.max_memory_bytes - bytes)
        return false;
      bytes += entry.snapshot->estimated_bytes;
    }
    return true;
  };
  if (!add(candidate))
    return false;
  for (const auto &[id, entry] : cursors_)
    if (id != replacing && !add(entry))
      return false;
  return true;
}

MatchReply CursorRegistry::commit(
    std::shared_ptr<ResultCursor> cursor,
    ctk::clang_layer::MatchExecution execution,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint, bool create,
    bool streaming) {
  if (!execution.state)
    return failure(MatchCode::Internal,
                   "backend returned no binding ownership");
  if (cursor->response.result_revision() ==
      std::numeric_limits<std::uint64_t>::max())
    return failure(MatchCode::ResourceExhausted, "cursor revision exhausted");
  ctk::match::v1::MatchResponse next;
  if (create)
    cursor->id = new_id();
  next.set_session_id(cursor->id);
  next.set_result_revision(cursor->response.result_revision() + 1);
  for (auto &row : execution.rows)
    next.add_results()->Swap(&row);
  const auto expiration = std::chrono::system_clock::now() + settings_.idle_ttl;
  const auto nanos = std::chrono::duration_cast<std::chrono::nanoseconds>(
                         expiration.time_since_epoch())
                         .count();
  next.mutable_expires_at()->set_seconds(nanos / 1000000000);
  next.mutable_expires_at()->set_nanos(nanos % 1000000000);
  if (!streaming && next.ByteSizeLong() > settings_.results.max_bytes)
    return failure(MatchCode::ResourceExhausted,
                   "complete match response exceeds byte limit (limit " +
                       std::to_string(settings_.results.max_bytes) +
                       " bytes, response " +
                       std::to_string(next.ByteSizeLong()) +
                       " bytes); increase server.grpc.max_send_message_bytes "
                       "and client.grpc.max_receive_message_bytes; "
                       "no cursor state committed");
  ctk::match::v1::MatchResponse retained;
  retained.set_session_id(next.session_id());
  retained.set_result_revision(next.result_revision());
  retained.mutable_expires_at()->CopyFrom(next.expires_at());
  for (const auto &row : next.results()) {
    auto *metadata = retained.add_results();
    if (row.has_source_match_index())
      metadata->set_source_match_index(row.source_match_index());
    for (const auto &[name, binding] : row.bindings()) {
      auto &thin = (*metadata->mutable_bindings())[name];
      for (const auto scope : binding.supported_scopes())
        thin.add_supported_scopes(
            static_cast<ctk::match::v1::BindingMatchScope>(scope));
    }
  }
  Entry candidate{cursor, execution.state->snapshot(),
                  retained.ByteSizeLong() + execution.state->retained_bytes() +
                      sizeof(ResultCursor)};
  // Copy before committing; allocation failure cannot publish a partial
  // revision.
  MatchReply reply;
  reply.response.CopyFrom(next);
  std::lock_guard guard(mutex_);
  if (create && cursors_.size() >= settings_.max_cursors)
    return failure(MatchCode::ResourceExhausted, "cursor count limit exceeded");
  if (!create) {
    const auto found = cursors_.find(cursor->id);
    if (found == cursors_.end() || found->second.cursor != cursor ||
        cursor->closed)
      return failure(MatchCode::NotFound, "cursor unavailable");
  }
  if (!fits(create ? "" : cursor->id, candidate))
    return failure(MatchCode::ResourceExhausted,
                   "retained cursor memory limit exceeded");
  if (!checkpoint())
    return failure(MatchCode::Cancelled, "cancelled before cursor commit");
  if (create) {
    if (!cursors_.emplace(cursor->id, candidate).second)
      return failure(MatchCode::Internal, "cursor identity collision");
  } else {
    cursors_.at(cursor->id) = std::move(candidate);
  }
  cursor->response.Swap(&retained);
  // execution retains the old native state until after the registry guard is
  // destroyed; AST/store ownership must never be released under this lock.
  cursor->state.swap(execution.state);
  cursor->deadline = std::chrono::steady_clock::now() + settings_.idle_ttl;
  return reply;
}

MatchReply CursorRegistry::close(const std::string &owner,
                                 const std::string &id) {
  if (!valid_id(id))
    return failure(MatchCode::InvalidArgument,
                   "session_id must be a canonical UUIDv4");
  const auto cursor = find(owner, id);
  if (!cursor)
    return {};
  std::lock_guard operation(cursor->operation);
  cursor->closed = true;
  {
    std::lock_guard guard(mutex_);
    cursors_.erase(id);
  }
  cursor->state.reset();
  cursor->response.Clear();
  return {};
}
} // namespace ctk::application::detail
