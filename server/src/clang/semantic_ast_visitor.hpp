#pragma once
#include "ctk/clang/traversal_backend.hpp"
#include <clang/AST/ASTTypeTraits.h>
#include <clang/AST/RecursiveASTVisitor.h>

namespace ctk::clang_layer {
class SemanticAstVisitor final
    : public clang::RecursiveASTVisitor<SemanticAstVisitor> {
public:
  SemanticAstVisitor(clang::ASTContext &context,
                     const ctk::analysis::v1::TraverseRequest &request,
                     const IMatchBackend::Checkpoint &checkpoint,
                     const TraversalLimits &limits, TraversalResult &result);
  bool shouldVisitImplicitCode() const;
  bool shouldVisitTemplateInstantiations() const;
  bool TraverseDecl(clang::Decl *declaration);
  bool dataTraverseStmtPre(clang::Stmt *statement);
  bool dataTraverseStmtPost(clang::Stmt *statement);

private:
  bool enter(const clang::DynTypedNode &node);
  clang::ASTContext &context_;
  const ctk::analysis::v1::TraverseRequest &request_;
  const IMatchBackend::Checkpoint &checkpoint_;
  const TraversalLimits &limits_;
  TraversalResult &result_;
  std::vector<std::uint64_t> parents_;
  std::size_t bytes_{};
};
} // namespace ctk::clang_layer
