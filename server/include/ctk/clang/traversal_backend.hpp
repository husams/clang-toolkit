#pragma once
#include "analysis/v1/traverse_request.pb.h"
#include "ctk/clang/traversal_limits.hpp"
#include "ctk/clang/traversal_result.hpp"

namespace ctk::clang_layer {
class ITraversalBackend {
public:
  using NodeSink = std::function<MatchCode(
      const ctk::analysis::v1::TraversalNode &, std::string &)>;
  virtual TraversalResult
  traverse_stream(const ctk::analysis::v1::TraverseRequest &request,
                  std::shared_ptr<const NativeBindingState> previous,
                  const IMatchBackend::Checkpoint &checkpoint,
                  const TraversalLimits &limits, const NodeSink &sink) {
    if (previous)
      return {MatchCode::FailedPrecondition,
              "retained traversal is unavailable",
              {}};
    auto result = traverse(request, checkpoint, limits);
    if (result.code == MatchCode::Ok) {
      for (const auto &node : result.response.nodes()) {
        result.code = sink(node, result.message);
        if (result.code != MatchCode::Ok)
          break;
      }
      result.node_count = result.response.nodes_size();
      result.response.clear_nodes();
    }
    return result;
  }
  virtual ~ITraversalBackend() = default;
  virtual TraversalResult traverse(const ctk::analysis::v1::TraverseRequest &,
                                   const IMatchBackend::Checkpoint &,
                                   const TraversalLimits &) = 0;
};
std::shared_ptr<ITraversalBackend>
make_traversal_backend(std::shared_ptr<IQueryEngine> engine = {});
} // namespace ctk::clang_layer
