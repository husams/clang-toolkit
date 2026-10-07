#pragma once
#include "ctk/clang/tooling.hpp"
#include "ctk/script/error.hpp"
#include <filesystem>
#include <map>
#include <tuple>
#include <unordered_set>
namespace ctk::application::detail {
// Request-local ownership: each file/profile observes one AST generation.
class PinnedQueryEngine final : public ctk::clang_layer::IQueryEngine {
public:
  PinnedQueryEngine(std::shared_ptr<IQueryEngine> engine,
                    std::uint64_t max_bytes)
      : engine_(std::move(engine)), max_bytes_(max_bytes) {}
  ctk::cache::SnapshotPtr
  acquire_snapshot(const ctk::clang_layer::FileInput &file) override {
    const auto directory =
        std::filesystem::path(file.working_directory).lexically_normal();
    const auto path = std::filesystem::path(file.path);
    const auto absolute =
        (path.is_absolute() ? path : directory / path).lexically_normal();
    const auto key = std::make_tuple(absolute.string(), directory.string(),
                                     file.compile_arguments);
    if (auto found = snapshots_.find(key); found != snapshots_.end())
      return found->second;
    auto snapshot = engine_->acquire_snapshot(file);
    if (snapshot) {
      const bool distinct = !owners_.contains(snapshot.get());
      if (distinct && (bytes_ > max_bytes_ ||
                       snapshot->estimated_bytes > max_bytes_ - bytes_))
        throw ctk::script::Error(ctk::clang_layer::MatchCode::ResourceExhausted,
                                 "script snapshot memory limit exceeded");
      if (distinct) {
        bytes_ += snapshot->estimated_bytes;
        owners_.insert(snapshot.get());
      }
      snapshots_.emplace(key, snapshot);
    }
    return snapshot;
  }
  ctk::clang_layer::QueryResult match(const ctk::clang_layer::FileInput &,
                                      const std::string &, const Checkpoint &,
                                      const MatchCallback &) override {
    throw std::logic_error(
        "pinned query engine supports retained operations only");
  }

private:
  std::shared_ptr<IQueryEngine> engine_;
  using Key = std::tuple<std::string, std::string, std::vector<std::string>>;
  std::map<Key, ctk::cache::SnapshotPtr> snapshots_;
  std::unordered_set<const ctk::cache::SnapshotEntry *> owners_;
  std::uint64_t bytes_ = 0;
  std::uint64_t max_bytes_;
};
} // namespace ctk::application::detail
