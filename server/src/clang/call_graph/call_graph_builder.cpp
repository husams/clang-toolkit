#include "call_graph_builder.hpp"
#include <clang/AST/ASTContext.h>
#include <clang/Basic/SourceManager.h>
namespace ctk::clang_layer::calls {
bool CallGraphBuilder::TraverseDecl(clang::Decl *declaration) {
  budget_.check();
  if (main_file_only_ && declaration &&
      !llvm::isa<clang::TranslationUnitDecl>(declaration) &&
      declaration->getLocation().isValid()) {
    const auto &sources = declaration->getASTContext().getSourceManager();
    const auto location = sources.getExpansionLoc(declaration->getLocation());
    if (!sources.isWrittenInMainFile(location))
      return true;
  }
  const auto success = clang::CallGraph::TraverseDecl(declaration);
  budget_.check();
  if (defer_node_limit_ || !budget_.limits.max_nodes ||
      size() <= budget_.limits.max_nodes)
    return success;
  std::size_t emitted = 1; // The synthetic root is part of the node budget.
  for (const auto &entry : *this) {
    const auto *node = entry.second.get();
    if (node == getRoot())
      continue;
    const auto *decl = node->getDecl();
    if (!decl || (scope_ && scope_(decl)) ||
        (!scope_ &&
         (!main_file_only_ ||
          decl->getASTContext().getSourceManager().isWrittenInMainFile(
              decl->getASTContext().getSourceManager().getExpansionLoc(
                  decl->getLocation())))))
      ++emitted;
  }
  if (emitted > budget_.limits.max_nodes)
    throw CallGraphFailure(MatchCode::ResourceExhausted,
                           "call graph node limit exceeded");
  return success;
}
} // namespace ctk::clang_layer::calls
