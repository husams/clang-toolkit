#include "ctk/clang/traversal_backend.hpp"
#include "captured_binding_state.hpp"
#include "ctk/clang/tooling.hpp"
#include "native_snapshot_owner.hpp"
#include "semantic_ast_visitor.hpp"

namespace ctk::clang_layer {
namespace {
class TraversalBackend final : public ITraversalBackend {
public:
  explicit TraversalBackend(std::shared_ptr<IQueryEngine> engine)
      : engine_(std::move(engine)) {}
  TraversalResult traverse(const ctk::analysis::v1::TraverseRequest &request,
                           const IMatchBackend::Checkpoint &checkpoint,
                           const TraversalLimits &limits) override {
    return run(request, {}, checkpoint, limits, {});
  }
  TraversalResult
  traverse_stream(const ctk::analysis::v1::TraverseRequest &request,
                  std::shared_ptr<const NativeBindingState> previous,
                  const IMatchBackend::Checkpoint &checkpoint,
                  const TraversalLimits &limits,
                  const NodeSink &sink) override {
    return run(request, std::move(previous), checkpoint, limits, sink);
  }
  TraversalResult run(const ctk::analysis::v1::TraverseRequest &request,
                      std::shared_ptr<const NativeBindingState> previous,
                      const IMatchBackend::Checkpoint &checkpoint,
                      const TraversalLimits &limits, const NodeSink &sink) {
    TraversalResult result;
    try {
      if (!checkpoint())
        return {MatchCode::Cancelled, "AST traversal cancelled", {}};
      ctk::cache::SnapshotPtr snapshot;
      if (request.has_file()) {
        const auto &file = request.file();
        snapshot = engine_->acquire_snapshot(
            {file.file_path(),
             {file.compile_arguments().begin(), file.compile_arguments().end()},
             file.working_directory(),
             file.compilation_database(),
             file.frozen_profile()});
      } else if (previous) {
        snapshot = previous->snapshot();
      }
      if (!snapshot)
        return {
            MatchCode::FailedPrecondition, "native snapshot unavailable", {}};
      std::lock_guard lane(snapshot->execution_mutex());
      const auto owner =
          std::dynamic_pointer_cast<const AstSnapshotOwner>(snapshot->owner);
      if (!owner || !owner->unit)
        return {MatchCode::Internal, "invalid native snapshot owner", {}};
      auto &context = owner->unit->getASTContext();
      SemanticAstVisitor visitor(context, request, checkpoint, limits, result,
                                 sink);
      bool complete = true;
      if (request.has_binding()) {
        const auto state =
            std::dynamic_pointer_cast<const CapturedBindingState>(previous);
        if (!state)
          return {
              MatchCode::FailedPrecondition, "native bindings unavailable", {}};
        const auto &target = request.binding();
        bool selected = false;
        for (std::size_t i = 0; i < state->rows.size(); ++i) {
          if (target.has_match_index() && i != target.match_index())
            continue;
          const auto found = state->rows[i].find(target.bind());
          if (found == state->rows[i].end())
            continue;
          selected = true;
          if (!visitor.traverse_node(found->second)) {
            complete = false;
            break;
          }
        }
        if (!selected && target.has_match_index())
          return {MatchCode::NotFound, "binding or row unavailable", {}};
        if (!selected && !state->rows.empty())
          return {MatchCode::NotFound, "binding unavailable", {}};
      } else {
        complete = visitor.traverse_node(
            clang::DynTypedNode::create(*context.getTranslationUnitDecl()));
      }
      if (!checkpoint())
        result.code = MatchCode::Cancelled;
      else if (!complete && result.code == MatchCode::Ok)
        result.code = MatchCode::Internal;
      else if (!sink && result.response.ByteSizeLong() > limits.max_bytes)
        result.code = MatchCode::ResourceExhausted;
      if (result.code != MatchCode::Ok) {
        if (result.message.empty())
          result.message = "AST traversal could not complete within limits";
        result.response.Clear();
      }
      return result;
    } catch (const std::exception &error) {
      return {MatchCode::InvalidArgument, error.what(), {}};
    }
  }

private:
  std::shared_ptr<IQueryEngine> engine_;
};
} // namespace
std::shared_ptr<ITraversalBackend>
make_traversal_backend(std::shared_ptr<IQueryEngine> engine) {
  return std::make_shared<TraversalBackend>(engine ? std::move(engine)
                                                   : make_query_engine());
}
} // namespace ctk::clang_layer
