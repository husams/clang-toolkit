#include "ctk/clang/traversal_backend.hpp"
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
    TraversalResult result;
    try {
      if (!checkpoint())
        return {MatchCode::Cancelled, "AST traversal cancelled", {}};
      const auto &file = request.file();
      const auto snapshot = engine_->acquire_snapshot(
          {file.file_path(),
           {file.compile_arguments().begin(), file.compile_arguments().end()},
           file.working_directory(), file.compilation_database(),
           file.frozen_profile()});
      if (!snapshot)
        return {
            MatchCode::FailedPrecondition, "native snapshot unavailable", {}};
      std::lock_guard lane(snapshot->execution_mutex());
      const auto owner =
          std::dynamic_pointer_cast<const AstSnapshotOwner>(snapshot->owner);
      if (!owner || !owner->unit)
        return {MatchCode::Internal, "invalid native snapshot owner", {}};
      auto &context = owner->unit->getASTContext();
      SemanticAstVisitor visitor(context, request, checkpoint, limits, result);
      const bool complete = visitor.TraverseAST(context);
      if (!checkpoint())
        result.code = MatchCode::Cancelled;
      else if (!complete && result.code == MatchCode::Ok)
        result.code = MatchCode::Internal;
      else if (result.response.ByteSizeLong() > limits.max_bytes)
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
