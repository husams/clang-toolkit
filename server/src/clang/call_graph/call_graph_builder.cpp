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
    if (!sources.isWrittenInMainFile(
            sources.getExpansionLoc(declaration->getLocation())))
      return true;
  }
  const auto success = clang::CallGraph::TraverseDecl(declaration);
  budget_.check();
  if (size() <= budget_.limits.max_nodes)
    return success;
  std::size_t emitted = 0;
  if (!main_file_only_)
    emitted = size();
  else for (const auto &entry : *this) {
    const auto *node = entry.second.get();
    const auto *decl = node->getDecl();
    if (!decl || !main_file_only_ ||
        decl->getASTContext().getSourceManager().isWrittenInMainFile(
            decl->getASTContext().getSourceManager().getExpansionLoc(
                decl->getLocation())))
      ++emitted;
  }
  if (emitted > budget_.limits.max_nodes)
    throw CallGraphFailure(MatchCode::ResourceExhausted,
                           "call graph node limit exceeded");
  return success;
}
} // namespace ctk::clang_layer::calls
