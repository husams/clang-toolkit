#pragma once
#include "analysis/v1/call_graph_request.pb.h"
#include "analysis/v1/call_graph_stream.pb.h"
#include "ctk/clang/call_graph_limits.hpp"
#include "ctk/clang/call_graph_result.hpp"
namespace ctk::clang_layer {
class ICallGraphBackend {
public:
  using EventSink = std::function<MatchCode(
      const ctk::analysis::v1::CallGraphStreamEvent &, std::string &)>;
  virtual ~ICallGraphBackend() = default;
  virtual CallGraphResult build(const ctk::analysis::v1::CallGraphRequest &,
                                const IMatchBackend::Checkpoint &,
                                const CallGraphLimits &) = 0;
  virtual CallGraphResult build_selected(
      const ctk::analysis::v1::CallGraphRequest &request,
      std::shared_ptr<const NativeBindingState>,
      const IMatchBackend::Checkpoint &checkpoint,
      const CallGraphLimits &limits) {
    return build(request, checkpoint, limits);
  }
  virtual CallGraphStreamResult build_stream(
      const ctk::analysis::v1::CallGraphRequest &request,
      std::shared_ptr<const NativeBindingState> previous,
      const IMatchBackend::Checkpoint &checkpoint,
      const CallGraphLimits &limits, const EventSink &sink) = 0;
};
std::shared_ptr<ICallGraphBackend>
make_call_graph_backend(std::shared_ptr<IQueryEngine> engine = {});
} // namespace ctk::clang_layer
