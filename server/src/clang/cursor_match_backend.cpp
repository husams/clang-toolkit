#include "captured_binding_state.hpp"
#include "ctk/clang/matching.hpp"
#include "ctk/clang/tooling.hpp"
#include "match_row_collector.hpp"
#include "native_snapshot_owner.hpp"
#include <clang/ASTMatchers/ASTMatchFinder.h>
#include <clang/ASTMatchers/ASTMatchers.h>
#include <clang/ASTMatchers/Dynamic/Diagnostics.h>
#include <clang/ASTMatchers/Dynamic/Parser.h>
#include <mutex>

namespace ctk::clang_layer {
namespace {
using namespace clang::ast_matchers;
using namespace ctk::match::v1;

// Native matchAST supplies the authoritative traversal. Restrict candidate
// roots by native ancestry; relationship predicates still see the full AST.
// A separate traversal per selected row preserves overlap and empty callbacks.
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

class CursorMatchBackend final : public IMatchBackend {
public:
  explicit CursorMatchBackend(std::shared_ptr<IQueryEngine> engine)
      : engine_(std::move(engine)) {}
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
                                     request.working_directory(), request.compilation_database()});
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
      return failure(MatchCode::InvalidArgument, error.what());
    }
  }
  MatchExecution execute(const MatchRequest &request,
                         std::shared_ptr<const NativeBindingState> previous,
                         const Checkpoint &checkpoint,
                         const MatchLimits &limits) override {
    MatchExecution result;
    dynamic::Diagnostics diagnostics;
    llvm::StringRef text(request.query());
    auto parsed = dynamic::Parser::parseMatcherExpression(text, &diagnostics);
    if (!parsed)
      return failure(MatchCode::InvalidArgument, diagnostics.toStringFull());
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
             file.working_directory(), file.compilation_database()});
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
      RowCollector callback(result, *state, checkpoint, limits);
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
            MatchFinder descendants;
            auto wrapped =
                scoped_matcher(root, query).withTraversalKind(traversal);
            descendants.addDynamicMatcher(wrapped, &callback);
            descendants.matchAST(context);
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
      return failure(MatchCode::InvalidArgument, error.what());
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
