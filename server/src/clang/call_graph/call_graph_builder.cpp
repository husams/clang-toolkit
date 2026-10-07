#include "call_graph_builder.hpp"
namespace ctk::clang_layer::calls {
bool CallGraphBuilder::TraverseDecl(clang::Decl *declaration) {
  budget_.check();
  const auto success = clang::CallGraph::TraverseDecl(declaration);
  budget_.check();
  if (size() > budget_.limits.max_nodes)
    throw CallGraphFailure(MatchCode::ResourceExhausted,
                           "call graph node limit exceeded");
  return success;
}
} // namespace ctk::clang_layer::calls
