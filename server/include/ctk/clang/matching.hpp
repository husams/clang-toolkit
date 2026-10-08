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
  std::size_t max_bytes{2147483648ULL};
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
  using RowSink = std::function<MatchCode(const ctk::match::v1::MatchResult &,
                                          std::string &)>;
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
  // Backends with native callback access should override this to emit rows
  // during traversal. The fallback preserves compatibility for test/custom
  // backends, though it cannot provide early delivery.
  virtual MatchExecution
  execute_stream(const ctk::match::v1::MatchRequest &request,
                 std::shared_ptr<const NativeBindingState> previous,
                 const Checkpoint &checkpoint, const MatchLimits &limits,
                 const RowSink &sink) {
    auto result = execute(request, std::move(previous), checkpoint, limits);
    if (result.code != MatchCode::Ok)
      return result;
    for (const auto &row : result.rows) {
      std::string message;
      const auto code = sink(row, message);
      if (code != MatchCode::Ok) {
        result.code = code;
        result.message = std::move(message);
        result.rows.clear();
        result.state.reset();
        break;
      }
    }
    return result;
  }
};
std::shared_ptr<IMatchBackend>
make_match_backend(std::shared_ptr<IQueryEngine> engine = {});
} // namespace ctk::clang_layer
