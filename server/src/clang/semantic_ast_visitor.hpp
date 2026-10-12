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
                     const TraversalLimits &limits, TraversalResult &result,
                     const ITraversalBackend::NodeSink &sink = {});
  using Base = clang::RecursiveASTVisitor<SemanticAstVisitor>;
  using NativeNNS = decltype(std::declval<clang::NestedNameSpecifierLoc>()
                                 .getNestedNameSpecifier());
  bool traverse_node(const clang::DynTypedNode &);
  bool TraverseType(clang::QualType, bool qualifier = true);
  bool TraverseTypeLoc(clang::TypeLoc, bool qualifier = true);
  bool TraverseAttr(clang::Attr *);
  bool TraverseNestedNameSpecifier(NativeNNS);
  bool TraverseNestedNameSpecifierLoc(clang::NestedNameSpecifierLoc);
  bool TraverseTemplateArgument(const clang::TemplateArgument &);
  bool TraverseTemplateArgumentLoc(const clang::TemplateArgumentLoc &);
  bool TraverseTemplateName(clang::TemplateName);
  bool TraverseCXXBaseSpecifier(const clang::CXXBaseSpecifier &);
  bool TraverseConstructorInitializer(clang::CXXCtorInitializer *);
  bool TraverseOMPClause(clang::OMPClause *);
  bool shouldVisitImplicitCode() const;
  bool shouldVisitTemplateInstantiations() const;
  bool TraverseDecl(clang::Decl *declaration);
  bool dataTraverseStmtPre(clang::Stmt *statement);
  bool dataTraverseStmtPost(clang::Stmt *statement);

private:
  bool enter(const clang::DynTypedNode &node, bool leaf = false);
  bool around(const clang::DynTypedNode &node,
              const std::function<bool()> &visit, bool leaf = false);
  clang::ASTContext &context_;
  const ctk::analysis::v1::TraverseRequest &request_;
  const IMatchBackend::Checkpoint &checkpoint_;
  const TraversalLimits &limits_;
  TraversalResult &result_;
  std::vector<std::uint64_t> parents_;
  std::size_t bytes_{};
  ITraversalBackend::NodeSink sink_;
  bool explicit_root_{};
};
} // namespace ctk::clang_layer
