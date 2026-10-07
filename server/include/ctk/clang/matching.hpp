#pragma once

#include "ctk/cache/snapshot.hpp"
#include "match/v1/match_service.pb.h"
#include <functional>
#include <memory>
#include <string>
#include <vector>

namespace ctk::clang_layer {
class IQueryEngine;
enum class MatchCode {
  Ok,
  InvalidArgument,
  NotFound,
  FailedPrecondition,
  ResourceExhausted,
  Cancelled,
  Aborted,
  Internal
};
struct MatchLimits {
  std::size_t max_rows{100000};
  std::size_t max_bytes{4 * 1024 * 1024 - 4096};
};
// Native wrapper values remain opaque; callers independently pin the snapshot.
class NativeBindingState {
public:
  virtual ~NativeBindingState() = default;
  virtual ctk::cache::SnapshotPtr snapshot() const = 0;
  virtual std::size_t retained_bytes() const = 0;
};
struct MatchExecution {
  MatchCode code{MatchCode::Ok};
  std::string message;
  std::vector<ctk::match::v1::MatchResult> rows;
  std::shared_ptr<const NativeBindingState> state;
};
class IMatchBackend {
public:
  using Checkpoint = std::function<bool()>;
  virtual ~IMatchBackend() = default;
  virtual MatchExecution parse(const ctk::match::v1::ParseRequest &,
                               const Checkpoint &, const MatchLimits &) {
    MatchExecution result;
    result.code = MatchCode::FailedPrecondition;
    result.message = "native parsing is unavailable";
    return result;
  }
  virtual MatchExecution
  execute(const ctk::match::v1::MatchRequest &request,
          std::shared_ptr<const NativeBindingState> previous,
          const Checkpoint &checkpoint, const MatchLimits &limits) = 0;
};
std::shared_ptr<IMatchBackend>
make_match_backend(std::shared_ptr<IQueryEngine> engine = {});
} // namespace ctk::clang_layer
