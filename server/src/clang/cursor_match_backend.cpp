#include "captured_binding_state.hpp"
#include "ctk/clang/matching.hpp"
#include "ctk/clang/tooling.hpp"
#include "match_row_collector.hpp"
#include "native_snapshot_owner.hpp"
#include <clang/ASTMatchers/ASTMatchFinder.h>
#include <clang/ASTMatchers/ASTMatchers.h>
#include <clang/ASTMatchers/Dynamic/Diagnostics.h>
#include <clang/ASTMatchers/Dynamic/Parser.h>
#include <clang/AST/RecursiveASTVisitor.h>
#include <functional>
#include <mutex>

namespace ctk::clang_layer {
namespace {
using namespace clang::ast_matchers;
using namespace ctk::match::v1;

MatchCode exception_code(const std::exception &error) {
  const std::string message = error.what();
  return message.find("estimate exceeds its limit") != std::string::npos
             ? MatchCode::ResourceExhausted
             : MatchCode::InvalidArgument;
}

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
        visit_lambda_body_(visit_lambda_body), should_continue_(should_continue) {}

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

  bool TraverseStmt(clang::Stmt *node,
                    DataRecursionQueue *queue = nullptr) {
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

  bool TraverseCXXRewrittenBinaryOperator(
      clang::CXXRewrittenBinaryOperator *node,
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

void match_subtree(const clang::DynTypedNode &root, MatchFinder &finder,
                   clang::ASTContext &context,
                   const std::function<bool()> &should_continue) {
  const auto *method = root.get<clang::CXXMethodDecl>();
  const bool lambda_call_operator_root =
      method && method->getParent()->isLambda() &&
      method->getParent()->getLambdaCallOperator() == method;
  SubtreeCandidateVisitor visitor(finder, context,
                                  lambda_call_operator_root, should_continue);
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

class CursorMatchBackend final : public IMatchBackend {
public:
  explicit CursorMatchBackend(std::shared_ptr<IQueryEngine> engine)
      : engine_(std::move(engine)) {}
  ctk::match::v1::CacheResources resources() const override {
    return engine_->resources();
  }
  void prune_caches(bool memory, bool disk) override {
    engine_->prune_caches(memory, disk);
  }
  MatchExecution parse(const ParseRequest &request,
                       const Checkpoint &checkpoint,
                       const MatchLimits &) override {
    try {
      if (!checkpoint())
        return failure(MatchCode::Cancelled, "parse cancelled");
      auto snapshot =
          engine_->acquire_snapshot({request.file_path(),
                                     {request.compile_arguments().begin(),
                                      request.compile_arguments().end()},
                                     request.working_directory(),
                                     request.compilation_database(),
                                     request.frozen_profile()});
      if (!snapshot)
        return failure(MatchCode::FailedPrecondition,
                       "native snapshot unavailable");
      std::lock_guard lane(snapshot->execution_mutex());
      const auto owner =
          std::dynamic_pointer_cast<const AstSnapshotOwner>(snapshot->owner);
      if (!owner || !owner->unit)
        return failure(MatchCode::Internal, "invalid native snapshot owner");
      if (!checkpoint())
        return failure(MatchCode::Cancelled, "parse cancelled");
      MatchExecution result;
      result.state =
          std::make_shared<CapturedBindingState>(std::move(snapshot));
      return result;
    } catch (const std::exception &error) {
      return failure(exception_code(error), error.what());
    }
  }
  MatchExecution execute(const MatchRequest &request,
                         std::shared_ptr<const NativeBindingState> previous,
                         const Checkpoint &checkpoint,
                         const MatchLimits &limits) override {
    return execute_impl(request, std::move(previous), checkpoint, limits,
                        nullptr);
  }
  MatchExecution
  execute_stream(const MatchRequest &request,
                 std::shared_ptr<const NativeBindingState> previous,
                 const Checkpoint &checkpoint, const MatchLimits &limits,
                 const RowSink &sink) override {
    return execute_impl(request, std::move(previous), checkpoint, limits,
                        &sink);
  }

private:
  MatchExecution
  execute_impl(const MatchRequest &request,
               std::shared_ptr<const NativeBindingState> previous,
               const Checkpoint &checkpoint, const MatchLimits &limits,
               const RowSink *sink) {
    MatchExecution result;
    dynamic::Diagnostics diagnostics;
    llvm::StringRef text(request.query());
    auto parsed = dynamic::Parser::parseMatcherExpression(text, &diagnostics);
    if (!parsed)
      return failure(MatchCode::InvalidArgument, diagnostics.toStringFull());
    if (auto root = parsed->tryBind("root"))
      parsed = std::move(root);
    const auto traversal =
        request.traversal_mode() ==
                MATCH_TRAVERSAL_MODE_IGNORE_UNLESS_SPELLED_IN_SOURCE
            ? clang::TK_IgnoreUnlessSpelledInSource
            : clang::TK_AsIs;
    auto query = parsed->withTraversalKind(traversal);
    try {
      if (!checkpoint())
        return failure(MatchCode::Cancelled, "query cancelled");
      ctk::cache::SnapshotPtr snapshot;
      const auto old =
          std::dynamic_pointer_cast<const CapturedBindingState>(previous);
      if (request.has_file()) {
        const auto &file = request.file();
        snapshot = engine_->acquire_snapshot(
            {file.file_path(),
             {file.compile_arguments().begin(), file.compile_arguments().end()},
             file.working_directory(),
             file.compilation_database(),
             file.frozen_profile()});
      } else if (old) {
        snapshot = old->snapshot();
      }
      if (!snapshot)
        return failure(MatchCode::FailedPrecondition,
                       "native snapshot unavailable");
      std::lock_guard lane(snapshot->execution_mutex());
      const auto owner =
          std::dynamic_pointer_cast<const AstSnapshotOwner>(snapshot->owner);
      if (!owner || !owner->unit)
        return failure(MatchCode::Internal, "invalid native snapshot owner");
      auto state = std::make_shared<CapturedBindingState>(snapshot);
      RowCollector callback(result, *state, checkpoint, limits, sink);
      MatchFinder finder;
      if (!finder.addDynamicMatcher(query, &callback))
        return failure(MatchCode::InvalidArgument,
                       "matcher is not a top-level AST matcher");
      auto &context = owner->unit->getASTContext();
      if (!request.has_binding()) {
        finder.matchAST(context);
      } else {
        const auto &target = request.binding();
        bool selected = false;
        for (std::size_t index = 0; index < old->rows.size(); ++index) {
          if (target.has_match_index() && target.match_index() != index)
            continue;
          const auto found = old->rows[index].find(target.bind());
          if (found == old->rows[index].end())
            continue;
          selected = true;
          const auto &root = found->second;
          const bool subtree = target.scope() != BINDING_MATCH_SCOPE_ROOT_ONLY;
          if (subtree &&
              (!(root.get<clang::Decl>() || root.get<clang::Stmt>()) ||
               !(query.canConvertTo<clang::Decl>() ||
                 query.canConvertTo<clang::Stmt>())))
            return failure(MatchCode::FailedPrecondition,
                           "subtree requires Decl/Stmt root and matcher");
          callback.source_row = index;
          if (subtree) {
            if (traversal == clang::TK_AsIs &&
                !requires_translation_unit_match_metadata(request.query())) {
              match_subtree(root, finder, context, [&] {
                return checkpoint() && result.code == MatchCode::Ok;
              });
            } else {
              MatchFinder descendants;
              auto wrapped =
                  scoped_matcher(root, query).withTraversalKind(traversal);
              descendants.addDynamicMatcher(wrapped, &callback);
              descendants.matchAST(context);
            }
          } else {
            finder.match(root, context);
          }
          if (result.code != MatchCode::Ok || !checkpoint())
            break;
        }
        if (!selected && !(request.preserve_source() && old->rows.empty() &&
                           !target.has_match_index()))
          return failure(MatchCode::NotFound, "binding or row unavailable");
      }
      if (!checkpoint())
        return failure(MatchCode::Cancelled, "query cancelled");
      if (result.code == MatchCode::Ok)
        result.state = std::move(state);
      else
        result.rows.clear();
      return result;
    } catch (const std::exception &error) {
      return failure(exception_code(error), error.what());
    }
  }

private:
  static MatchExecution failure(MatchCode code, std::string message) {
    MatchExecution result;
    result.code = code;
    result.message = std::move(message);
    return result;
  }
  std::shared_ptr<IQueryEngine> engine_;
};
} // namespace

std::shared_ptr<IMatchBackend>
make_match_backend(std::shared_ptr<IQueryEngine> engine) {
  return std::make_shared<CursorMatchBackend>(engine ? std::move(engine)
                                                     : make_query_engine());
}
} // namespace ctk::clang_layer
