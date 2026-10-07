#pragma once
#include "analysis/v1/call_graph_request.pb.h"
#include "ctk/clang/call_graph_limits.hpp"
#include "ctk/clang/call_graph_result.hpp"
namespace ctk::clang_layer {
class ICallGraphBackend {
public:
  virtual ~ICallGraphBackend() = default;
  virtual CallGraphResult build(const ctk::analysis::v1::CallGraphRequest &,
                                const IMatchBackend::Checkpoint &,
                                const CallGraphLimits &) = 0;
};
std::shared_ptr<ICallGraphBackend>
make_call_graph_backend(std::shared_ptr<IQueryEngine> engine = {});
} // namespace ctk::clang_layer
