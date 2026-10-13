#include "native_navigation.hpp"
#include "captured_binding_state.hpp"
#include "match_row_collector.hpp"
#include "native_snapshot_owner.hpp"
#include "semantic_ast_visitor.hpp"
#include <clang/AST/ParentMapContext.h>
#include <clang/ASTMatchers/Dynamic/Diagnostics.h>
#include <clang/ASTMatchers/Dynamic/Parser.h>

namespace ctk::clang_layer {
using namespace ctk::match::v1;
using namespace clang::ast_matchers;
namespace {
MatchExecution failure(MatchCode code, std::string message) {
  MatchExecution result;
  result.code = code;
  result.message = std::move(message);
  return result;
}
}
MatchExecution navigate_bindings(
    const MatchRequest &request,
    std::shared_ptr<const NativeBindingState> previous,
    const IMatchBackend::Checkpoint &checkpoint, const MatchLimits &limits,
    const IMatchBackend::RowSink *sink, bool retain_target) {
  const auto old =
      std::dynamic_pointer_cast<const CapturedBindingState>(previous);
  if (!old || !old->snapshot())
    return failure(MatchCode::FailedPrecondition, "native bindings unavailable");
  auto snapshot = old->snapshot();
  std::lock_guard lane(snapshot->execution_mutex());
  const auto owner =
      std::dynamic_pointer_cast<const AstSnapshotOwner>(snapshot->owner);
  if (!owner || !owner->unit)
    return failure(MatchCode::Internal, "invalid native snapshot owner");
  auto &context = owner->unit->getASTContext();
  const bool source_spelled = !retain_target && request.traversal_mode() ==
      MATCH_TRAVERSAL_MODE_IGNORE_UNLESS_SPELLED_IN_SOURCE;
  MatchExecution result;
  auto state = std::make_shared<CapturedBindingState>(snapshot);
  RowCollector callback(result, *state, checkpoint, limits, sink);
  MatchFinder finder;
  if (!request.query().empty()) {
    dynamic::Diagnostics diagnostics;
    llvm::StringRef text(request.query());
    auto query = dynamic::Parser::parseMatcherExpression(text, &diagnostics);
    if (!query)
      return failure(MatchCode::InvalidArgument, diagnostics.toStringFull());
    if (auto root = query->tryBind("root"))
      query = std::move(root);
    const auto traversal = source_spelled
        ? clang::TK_IgnoreUnlessSpelledInSource : clang::TK_AsIs;
    if (!finder.addDynamicMatcher(query->withTraversalKind(traversal),
                                  &callback))
      return failure(MatchCode::InvalidArgument,
                     "matcher is not a top-level AST matcher");
  }
  std::size_t examined = 0;
  const auto maximum = request.has_navigation_max_nodes()
                           ? request.navigation_max_nodes()
                           : 10000U;
  const auto visit = [&](const clang::DynTypedNode &candidate) {
    if (!checkpoint()) {
      result.code = MatchCode::Cancelled;
      result.message = "navigation cancelled";
      return false;
    }
    if (++examined > maximum) {
      result.code = MatchCode::ResourceExhausted;
      result.message = "navigation node limit exceeded";
      return false;
    }
    callback.candidate_node = candidate;
    if (retain_target)
      callback.target_node = candidate;
    if (request.query().empty())
      callback.emit({}, context);
    else
      finder.match(candidate, context);
    return result.code == MatchCode::Ok;
  };
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
    callback.source_row = index;
    if (request.navigation_axis() == NAVIGATION_AXIS_CHILDREN) {
      callback.target_parent = root;
      ctk::analysis::v1::TraverseRequest options;
      options.set_max_depth(1);
      options.set_visit_implicit_code(!source_spelled);
      options.set_visit_template_instantiations(!source_spelled);
      // One additional visit for the starting node, which is not a candidate.
      options.set_max_nodes(100001);
      TraversalResult walked;
      SemanticAstVisitor visitor(
          context, options, checkpoint, {100001, limits.max_bytes}, walked, {},
          [&](const clang::DynTypedNode &node, std::size_t depth,
              std::string &message) {
            if (depth == 1 && !visit(node)) {
              message = result.message;
              return result.code;
            }
            return MatchCode::Ok;
          });
      visitor.traverse_node(root);
      if (walked.code != MatchCode::Ok && result.code == MatchCode::Ok) {
        result.code = walked.code;
        result.message = walked.message;
      }
    } else {
      callback.target_parent.reset();
      if (root.get<clang::Decl>() || root.get<clang::Stmt>()) {
        for (const auto &parent : context.getParents(root))
          if (!visit(parent))
            break;
      } else if (index < old->navigation_parents.size() &&
                 old->navigation_parents[index].contains(target.bind())) {
        // Non-memoizable native value nodes retain their exact visitor edge.
        visit(old->navigation_parents[index].at(target.bind()));
      } else if (root.get<clang::Type>() || root.get<clang::TypeLoc>() ||
                 root.get<clang::NestedNameSpecifier>() ||
                 root.get<clang::NestedNameSpecifierLoc>()) {
        for (const auto &parent : context.getParents(root))
          if (!visit(parent))
            break;
      } else {
        return failure(MatchCode::FailedPrecondition,
                       "native parent lookup unavailable for this binding; "
                       "auxiliary children retain their navigation parent");
      }
    }
    if (result.code != MatchCode::Ok || !checkpoint())
      break;
  }
  if (!selected && !(old->rows.empty() && !target.has_match_index()))
    return failure(MatchCode::NotFound, "binding or row unavailable");
  if (!checkpoint())
    return failure(MatchCode::Cancelled, "navigation cancelled");
  if (result.code != MatchCode::Ok) {
    result.rows.clear();
    return result;
  }
  result.state = std::move(state);
  return result;
}
}
