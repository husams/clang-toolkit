#include "ctk/clang/cfg_backend.hpp"
#include "../native_snapshot_owner.hpp"
#include "cfg_function_collector.hpp"
#include "cfg_graph.hpp"
#include "cfg_options.hpp"
#include "../serialization/analysis_projection.hpp"
#include <algorithm>
namespace ctk::clang_layer {
namespace {
class CfgBackend final : public ICfgBackend {
public:
  explicit CfgBackend(std::shared_ptr<IQueryEngine> engine)
      : engine_(std::move(engine)) {}
  CfgResult build(const ctk::analysis::v1::CfgRequest &request,
                  const IMatchBackend::Checkpoint &checkpoint,
                  const CfgLimits &limits) override {
    namespace cf = control_flow;
    CfgResult result;
    try {
      cf::CfgBudget budget{checkpoint, limits};
      budget.limits.max_functions = std::min<std::size_t>(
          limits.max_functions,
          request.has_max_functions() ? request.max_functions() : 100);
      budget.limits.max_blocks = std::min<std::size_t>(
          limits.max_blocks,
          request.has_max_blocks() ? request.max_blocks() : 10000);
      budget.limits.max_elements = std::min<std::size_t>(
          limits.max_elements,
          request.has_max_elements() ? request.max_elements() : 100000);
      budget.check();
      const auto &file = request.file();
      const auto snapshot = engine_->acquire_snapshot(
          {file.file_path(),
           {file.compile_arguments().begin(), file.compile_arguments().end()},
           file.working_directory(), file.compilation_database()});
      if (!snapshot)
        return {
            MatchCode::FailedPrecondition, "native snapshot unavailable", {}};
      std::lock_guard lane(snapshot->execution_mutex());
      const auto owner =
          std::dynamic_pointer_cast<const AstSnapshotOwner>(snapshot->owner);
      if (!owner || !owner->unit)
        return {MatchCode::Internal, "invalid native snapshot owner", {}};
      auto &ast = owner->unit->getASTContext();
      cf::Context projection_context{ast};
      serialization::apply_projection(request.projection(), projection_context);
      cf::CfgFunctionCollector collector(request.function(), budget,
                                        request.main_file_only());
      collector.TraverseAST(ast);
      if (collector.definitions.empty())
        return {collector.dependent ? MatchCode::FailedPrecondition
                                    : MatchCode::NotFound,
                collector.dependent
                    ? "CFG requires a concrete function definition"
                    : "function definition not found",
                {}};
      const auto options = cf::build_options(request.options());
      for (auto *function : collector.definitions) {
        budget.check();
        auto graph =
            clang::CFG::buildCFG(function, function->getBody(), &ast, options);
        budget.check();
        if (!graph)
          throw cf::BuildFailure(MatchCode::FailedPrecondition,
                                 "Clang could not build the function CFG");
        cf::Context context{ast};
        serialization::apply_projection(request.projection(), context);
        cf::write_graph(*function, *graph, *result.response.add_graphs(),
                        context, budget);
      }
      budget.check();
      if (result.response.ByteSizeLong() > limits.max_bytes)
        throw cf::BuildFailure(MatchCode::ResourceExhausted,
                               "CFG response byte limit exceeded");
      return result;
    } catch (const cf::BuildFailure &error) {
      return {error.code, error.what(), {}};
    } catch (const std::exception &error) {
      return {MatchCode::InvalidArgument, error.what(), {}};
    }
  }

private:
  std::shared_ptr<IQueryEngine> engine_;
};
} // namespace
std::shared_ptr<ICfgBackend>
make_cfg_backend(std::shared_ptr<IQueryEngine> engine) {
  return std::make_shared<CfgBackend>(engine ? std::move(engine)
                                             : make_query_engine());
}
} // namespace ctk::clang_layer
