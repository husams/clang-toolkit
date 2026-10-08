#pragma once

#include "result_cursor.hpp"
#include <map>

namespace ctk::application::detail {
class CursorRegistry final {
public:
  explicit CursorRegistry(CursorSettings settings) : settings_(settings) {}
  static bool valid_id(const std::string &id);
  std::shared_ptr<ResultCursor> find(const std::string &owner,
                                     const std::string &id);
  // Caller holds cursor.operation; commit is one cancellation/revision
  // boundary.
  MatchReply
  commit(std::shared_ptr<ResultCursor> cursor,
         ctk::clang_layer::MatchExecution execution,
         const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint,
         bool create, bool streaming = false);
  MatchReply close(const std::string &owner, const std::string &id);

private:
  struct Entry {
    std::shared_ptr<ResultCursor> cursor;
    ctk::cache::SnapshotPtr snapshot;
    std::uint64_t binding_bytes;
  };
  bool fits(const std::string &replacing, const Entry &candidate) const;
  void prune();
  CursorSettings settings_;
  std::mutex mutex_;
  std::map<std::string, Entry> cursors_;
};
} // namespace ctk::application::detail
