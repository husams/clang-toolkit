#include "scoped_match.hpp"

#include <clang/AST/RecursiveASTVisitor.h>
#include <clang/ASTMatchers/ASTMatchers.h>

namespace ctk::clang_layer {
using namespace clang::ast_matchers;

// Preserve Clang's full MatchFinder traversal for source-spelled queries,
// whose candidate eligibility depends on contextual traversal state.
internal::DynTypedMatcher
scoped_matcher(const clang::DynTypedNode &root,
               const internal::DynTypedMatcher &query) {
  if (const auto *selected = root.get<clang::Decl>()) {
    if (query.canConvertTo<clang::Decl>())
      return decl(allOf(query.convertTo<clang::Decl>(),
                        anyOf(equalsNode(selected),
                              hasAncestor(decl(equalsNode(selected))))));
    return stmt(allOf(query.convertTo<clang::Stmt>(),
                      hasAncestor(decl(equalsNode(selected)))));
  }
  const auto *selected = root.get<clang::Stmt>();
  if (query.canConvertTo<clang::Decl>())
    return decl(allOf(query.convertTo<clang::Decl>(),
                      hasAncestor(stmt(equalsNode(selected)))));
  return stmt(allOf(
      query.convertTo<clang::Stmt>(),
      anyOf(equalsNode(selected), hasAncestor(stmt(equalsNode(selected))))));
}

bool requires_translation_unit_match_metadata(llvm::StringRef query) {
  // MatchASTVisitor gathers typedef aliases and Objective-C compatible aliases
  // before evaluating these inheritance matchers. Per-node MatchFinder::match
  // does not build that translation-unit cache.
  return query.contains("isDerivedFrom") ||
         query.contains("isDirectlyDerivedFrom") ||
         query.contains("isSameOrDerivedFrom");
}

namespace {
// MatchFinder::matchAST walks the whole translation unit. For a selected
// AS_IS subtree, mirror its RecursiveASTVisitor candidate walk from just that
// root and ask MatchFinder to evaluate each Decl/Stmt. Each exact-node match
// still has the full ASTContext available for relationship predicates.
class SubtreeCandidateVisitor final
    : public clang::RecursiveASTVisitor<SubtreeCandidateVisitor> {
public:
  using VisitorBase = clang::RecursiveASTVisitor<SubtreeCandidateVisitor>;

  SubtreeCandidateVisitor(MatchFinder &finder, clang::ASTContext &context,
                          bool visit_lambda_body,
                          const std::function<bool()> &should_continue)
      : finder_(finder), context_(context),
        visit_lambda_body_(visit_lambda_body),
        should_continue_(should_continue) {}

  bool shouldVisitTemplateInstantiations() const { return true; }
  bool shouldVisitImplicitCode() const { return true; }
  bool shouldVisitLambdaBody() const { return visit_lambda_body_; }

  bool TraverseDecl(clang::Decl *node) {
    if (!node)
      return true;
    if (!should_continue_())
      return false;
    finder_.match(clang::DynTypedNode::create(*node), context_);
    if (!should_continue_())
      return false;
    return VisitorBase::TraverseDecl(node);
  }

  bool TraverseStmt(clang::Stmt *node, DataRecursionQueue *queue = nullptr) {
    if (!node)
      return true;
    if (!should_continue_())
      return false;
    finder_.match(clang::DynTypedNode::create(*node), context_);
    if (!should_continue_())
      return false;
    return VisitorBase::TraverseStmt(node, queue);
  }

  bool TraverseCXXForRangeStmt(clang::CXXForRangeStmt *node,
                               DataRecursionQueue * = nullptr) {
    if (!node)
      return true;
    // MatchASTVisitor's init/loop-variable/range-init replay is marked
    // NotAsIs and does not emit candidates in the AS_IS traversal mode.
    for (clang::Stmt *child : node->children()) {
      if (child != node->getBody() && !TraverseStmt(child))
        return false;
    }
    return TraverseStmt(node->getBody());
  }

  bool
  TraverseCXXRewrittenBinaryOperator(clang::CXXRewrittenBinaryOperator *node,
                                     DataRecursionQueue * = nullptr) {
    if (!node)
      return true;
    // The separate decomposed LHS/RHS replay is NotAsIs; only walk the
    // rewritten operator's native children in this traversal mode.
    for (clang::Stmt *child : node->children())
      if (!TraverseStmt(child))
        return false;
    return true;
  }

  bool TraverseLambdaExpr(clang::LambdaExpr *node) {
    if (!node)
      return true;
    for (unsigned index = 0; index < node->capture_size(); ++index) {
      const clang::LambdaCapture *capture = node->capture_begin() + index;
      if (!TraverseLambdaCapture(node, capture,
                                 node->capture_init_begin()[index]))
        return false;
    }
    if (!TraverseDecl(node->getLambdaClass()))
      return false;

    // The separate written-signature replay is NotAsIs. With a selected
    // lambda call-operator root, traversing the lambda class also visits its
    // call-operator body; do not replay that same body here.
    return visit_lambda_body_ || TraverseStmt(node->getBody());
  }

private:
  MatchFinder &finder_;
  clang::ASTContext &context_;
  bool visit_lambda_body_;
  const std::function<bool()> &should_continue_;
};

} // namespace

void match_subtree(const clang::DynTypedNode &root, MatchFinder &finder,
                   clang::ASTContext &context,
                   const std::function<bool()> &should_continue) {
  const auto *method = root.get<clang::CXXMethodDecl>();
  const bool lambda_call_operator_root =
      method && method->getParent()->isLambda() &&
      method->getParent()->getLambdaCallOperator() == method;
  SubtreeCandidateVisitor visitor(finder, context, lambda_call_operator_root,
                                  should_continue);
  // Candidate callbacks come only from this rooted native walk. Some AST
  // expressions (such as an in-class initializer) are shared with field or
  // sibling-constructor occurrences elsewhere in the translation unit; those
  // outside-root occurrences are deliberately not imported here. The original
  // ASTContext remains available to each match for relationship predicates.
  if (const auto *decl = root.get<clang::Decl>())
    visitor.TraverseDecl(const_cast<clang::Decl *>(decl));
  else if (const auto *stmt = root.get<clang::Stmt>())
    visitor.TraverseStmt(const_cast<clang::Stmt *>(stmt));
}

} // namespace ctk::clang_layer
