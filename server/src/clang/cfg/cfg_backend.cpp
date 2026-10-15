#include "ctk/clang/cfg_backend.hpp"
#include "../captured_binding_state.hpp"
#include "../native_snapshot_owner.hpp"
#include "../serialization/analysis_projection.hpp"
#include "cfg_function_collector.hpp"
#include "cfg_graph.hpp"
#include "cfg_options.hpp"
#include <algorithm>
#include <clang/Basic/SourceManager.h>
namespace ctk::clang_layer {
namespace {
class CfgBackend final : public ICfgBackend {
public:
  explicit CfgBackend(std::shared_ptr<IQueryEngine> engine)
      : engine_(std::move(engine)) {}
  CfgResult build(const ctk::analysis::v1::CfgRequest &request,
                  const IMatchBackend::Checkpoint &checkpoint,
                  const CfgLimits &limits) override {
    return run(request, {}, checkpoint, limits, {});
  }
  CfgResult build_stream(const ctk::analysis::v1::CfgRequest &request,
                         std::shared_ptr<const NativeBindingState> previous,
                         const IMatchBackend::Checkpoint &checkpoint,
                         const CfgLimits &limits,
                         const EventSink &sink) override {
    return run(request, std::move(previous), checkpoint, limits, sink);
  }
  CfgResult run(const ctk::analysis::v1::CfgRequest &request,
                std::shared_ptr<const NativeBindingState> previous,
                const IMatchBackend::Checkpoint &checkpoint,
                const CfgLimits &limits, const EventSink &sink) {
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
      auto &ast = owner->unit->getASTContext();
      cf::Context projection_context{ast};
      serialization::apply_projection(request.projection(), projection_context);
      cf::CfgFunctionCollector collector(request.function(), budget,
                                         request.main_file_only());
      std::vector<const clang::FunctionDecl *> functions;
      if (request.has_binding()) {
        const auto state =
            std::dynamic_pointer_cast<const CapturedBindingState>(previous);
        if (!state)
          return {
              MatchCode::FailedPrecondition, "native bindings unavailable", {}};
        const auto &target = request.binding();
        bool selected = false;
        std::unordered_set<const clang::FunctionDecl *> seen;
        for (std::size_t i = 0; i < state->rows.size(); ++i) {
          budget.check();
          if (target.has_match_index() && i != target.match_index())
            continue;
          const auto found = state->rows[i].find(target.bind());
          if (found == state->rows[i].end())
            continue;
          selected = true;
          const auto *function = found->second.get<clang::FunctionDecl>();
          if (!function)
            return {MatchCode::InvalidArgument,
                    "CFG binding must be a function or method",
                    {}};
          const auto &sources = ast.getSourceManager();
          if (request.main_file_only() &&
              !sources.isWrittenInMainFile(
                  sources.getExpansionLoc(function->getLocation())))
            continue;
          if (!function->doesThisDeclarationHaveABody() ||
              function->isDependentContext())
            return {MatchCode::FailedPrecondition,
                    "CFG requires a concrete function definition",
                    {}};
          if (!seen.insert(function->getCanonicalDecl()).second)
            continue;
          if (functions.size() == budget.limits.max_functions)
            throw cf::BuildFailure(MatchCode::ResourceExhausted,
                                   "CFG function limit exceeded");
          functions.push_back(function);
        }
        if (!selected && (target.has_match_index() || !state->rows.empty()))
          return {MatchCode::NotFound, "binding or row unavailable", {}};
        if (selected && functions.empty())
          return {
              MatchCode::NotFound, "function definition outside main file", {}};
      } else {
        collector.TraverseAST(ast);
        functions.assign(collector.definitions.begin(),
                         collector.definitions.end());
      }
      if (functions.empty() && !request.has_binding())
        return {collector.dependent ? MatchCode::FailedPrecondition
                                    : MatchCode::NotFound,
                collector.dependent
                    ? "CFG requires a concrete function definition"
                    : "function definition not found",
                {}};
      const auto options = cf::build_options(request.options());
      for (const auto *function : functions) {
        budget.check();
        auto graph =
            clang::CFG::buildCFG(function, function->getBody(), &ast, options);
        budget.check();
        if (!graph)
          throw cf::BuildFailure(MatchCode::FailedPrecondition,
                                 "Clang could not build the function CFG");
        cf::Context context{ast};
        serialization::apply_projection(request.projection(), context);
        if (!sink) {
          cf::write_graph(*function, *graph, *result.response.add_graphs(),
                          context, budget);
          continue;
        }
        auto emit = [&](const ctk::analysis::v1::CfgStreamEvent &event) {
          budget.check();
          if (event.ByteSizeLong() > limits.max_bytes)
            throw cf::BuildFailure(MatchCode::ResourceExhausted,
                                   "CFG stream event byte limit exceeded");
          std::string message;
          const auto code = sink(event, message);
          if (code != MatchCode::Ok)
            throw cf::BuildFailure(code, message.empty() ? "CFG stream closed"
                                                         : message.c_str());
        };
        ctk::analysis::v1::CfgStreamEvent event;
        auto *started = event.mutable_graph_started();
        started->set_graph_index(result.graph_count);
        started->set_snapshot_generation(snapshot->generation);
        auto *header = started->mutable_graph();
        serialization::helpers::write_symbol(
            *function, *header->mutable_function(), context);
        header->set_entry_block(graph->getEntry().getBlockID());
        header->set_exit_block(graph->getExit().getBlockID());
        header->set_is_linear(graph->isLinear());
        cf::finish(*header, context);
        emit(event);
        bool complete = context.complete;
        const auto initial_blocks = budget.blocks,
                   initial_elements = budget.elements;
        std::vector<const clang::CFGBlock *> ordered(graph->begin(),
                                                     graph->end());
        std::sort(ordered.begin(), ordered.end(), [](auto *a, auto *b) {
          return a->getBlockID() < b->getBlockID();
        });
        for (const auto *block : ordered) {
          event.Clear();
          event.mutable_block()->set_graph_index(result.graph_count);
          auto child = cf::fresh_context(context);
          budget.bytes = 0; // Bound each block; counts remain request-wide.
          cf::write_block(*block, *event.mutable_block()->mutable_block(),
                          child, budget);
          complete &= child.complete;
          emit(event);
        }
        event.Clear();
        auto *completed = event.mutable_graph_completed();
        completed->set_graph_index(result.graph_count++);
        completed->set_block_count(budget.blocks - initial_blocks);
        completed->set_element_count(budget.elements - initial_elements);
        completed->set_is_complete(complete);
        emit(event);
      }
      budget.check();
      result.block_count = budget.blocks;
      result.element_count = budget.elements;
      if (!sink && result.response.ByteSizeLong() > limits.max_bytes)
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
