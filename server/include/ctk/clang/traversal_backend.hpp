#pragma once
#include "analysis/v1/traverse_request.pb.h"
#include "ctk/clang/traversal_limits.hpp"
#include "ctk/clang/traversal_result.hpp"

namespace ctk::clang_layer {
class ITraversalBackend {
public:
  virtual ~ITraversalBackend() = default;
  virtual TraversalResult traverse(const ctk::analysis::v1::TraverseRequest &,
                                   const IMatchBackend::Checkpoint &,
                                   const TraversalLimits &) = 0;
};
std::shared_ptr<ITraversalBackend>
make_traversal_backend(std::shared_ptr<IQueryEngine> engine = {});
} // namespace ctk::clang_layer
