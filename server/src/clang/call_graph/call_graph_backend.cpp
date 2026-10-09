#include "ctk/clang/call_graph_backend.hpp"
#include "../native_snapshot_owner.hpp"
#include "call_graph_builder.hpp"
#include "call_graph_edge.hpp"
#include "call_graph_node.hpp"
#include "declaration_order.hpp"
#include "../serialization/analysis_projection.hpp"
#include <clang/Basic/SourceManager.h>
#include <algorithm>
#include <unordered_map>
namespace ctk::clang_layer {
namespace {
class CallGraphBackend final : public ICallGraphBackend {
public:
  explicit CallGraphBackend(std::shared_ptr<IQueryEngine> engine)
      : engine_(std::move(engine)) {}
  CallGraphResult build(const ctk::analysis::v1::CallGraphRequest &request,
                        const IMatchBackend::Checkpoint &checkpoint,
                        const CallGraphLimits &limits) override {
    CallGraphResult result;
    try {
      calls::CallGraphBudget budget{checkpoint, limits};
      budget.limits.max_nodes = std::min<std::size_t>(
          limits.max_nodes,
          request.has_max_nodes() ? request.max_nodes() : 10000);
      budget.limits.max_edges = std::min<std::size_t>(
          limits.max_edges,
          request.has_max_edges() ? request.max_edges() : 100000);
      budget.check();
      const auto &file = request.file();
      auto snapshot = engine_->acquire_snapshot(
          {file.file_path(),
           {file.compile_arguments().begin(), file.compile_arguments().end()},
           file.working_directory(), file.compilation_database()});
      if (!snapshot)
        return {
            MatchCode::FailedPrecondition, "native snapshot unavailable", {}};
      std::lock_guard lane(snapshot->execution_mutex());
      auto owner =
          std::dynamic_pointer_cast<const AstSnapshotOwner>(snapshot->owner);
      if (!owner || !owner->unit)
        return {MatchCode::Internal, "invalid native snapshot owner", {}};
      auto &ast = owner->unit->getASTContext();
      calls::CallGraphBuilder graph(budget, request.main_file_only());
      if (request.has_visit_implicit_code())
        graph.ShouldVisitImplicitCode = request.visit_implicit_code();
      if (request.has_visit_template_instantiations())
        graph.ShouldVisitTemplateInstantiations =
            request.visit_template_instantiations();
      graph.addToCallGraph(ast.getTranslationUnitDecl());
      calls::DeclarationOrder order(budget);
      order.TraverseAST(ast);
      std::vector<const clang::CallGraphNode *> nodes{graph.getRoot()};
      auto included = [&](const clang::CallGraphNode *node) {
        if (!request.main_file_only() || !node->getDecl())
          return true;
        const auto &sources = ast.getSourceManager();
        return sources.isWrittenInMainFile(
            sources.getExpansionLoc(node->getDecl()->getLocation()));
      };
      for (const auto &entry : graph)
        if (entry.second.get() != graph.getRoot() && included(entry.second.get()))
          nodes.push_back(entry.second.get());
      // Every callable declaration must be in the complete AST visitor order;
      // reject an unaccounted node instead of publishing address-dependent
      // indices.
      for (std::size_t i = 1; i < nodes.size(); ++i)
        if (!order.ordinals.contains(nodes[i]->getDecl()->getCanonicalDecl()))
          throw calls::CallGraphFailure(
              MatchCode::Internal,
              "call graph declaration missing from native visitor order");
      std::sort(nodes.begin() + 1, nodes.end(), [&order](auto *a, auto *b) {
        return order.ordinals.at(a->getDecl()->getCanonicalDecl()) <
               order.ordinals.at(b->getDecl()->getCanonicalDecl());
      });
      std::unordered_map<const clang::CallGraphNode *, std::size_t> indices;
      result.response.set_is_complete(true);
      result.response.set_main_file_only(request.main_file_only());
      for (std::size_t index = 0; index < nodes.size(); ++index) {
        budget.check();
        indices.emplace(nodes[index], index);
        serialization::SerializationContext context{ast};
        serialization::apply_projection(request.projection(), context);
        auto *value = result.response.add_nodes();
        value->set_node_index(index);
        calls::write_node(*nodes[index], *value, context);
        result.response.set_is_complete(result.response.is_complete() &&
                                        context.complete);
        for (const auto &entry : context.availability)
          result.response.add_availability()->CopyFrom(entry);
        budget.add_bytes(value->ByteSizeLong());
      }
      for (std::size_t index = 0; index < nodes.size(); ++index)
        for (const auto &record : nodes[index]->callees()) {
          budget.check();
          if (request.main_file_only() && !indices.contains(record.Callee)) {
            result.response.set_external_edges_omitted(
                result.response.external_edges_omitted() + 1);
            continue;
          }
          if (++budget.edges > budget.limits.max_edges)
            throw calls::CallGraphFailure(MatchCode::ResourceExhausted,
                                          "call graph edge limit exceeded");
          if (!indices.contains(record.Callee))
            throw calls::CallGraphFailure(
                MatchCode::Internal, "call graph callee missing from graph");
          serialization::SerializationContext context{ast};
          serialization::apply_projection(request.projection(), context);
          auto *value = result.response.add_edges();
          value->set_caller_node(index);
          value->set_callee_node(indices.at(record.Callee));
          value->set_is_virtual_root_edge(index == 0);
          calls::write_edge(record, *value, context);
          result.response.set_is_complete(result.response.is_complete() &&
                                          context.complete);
          for (const auto &entry : context.availability)
            result.response.add_availability()->CopyFrom(entry);
          budget.add_bytes(value->ByteSizeLong());
        }
      budget.check();
      if (result.response.ByteSizeLong() > limits.max_bytes)
        throw calls::CallGraphFailure(
            MatchCode::ResourceExhausted,
            "call graph response byte limit exceeded");
      return result;
    } catch (const calls::CallGraphFailure &error) {
      return {error.code, error.what(), {}};
    } catch (const std::exception &error) {
      return {MatchCode::InvalidArgument, error.what(), {}};
    }
  }

private:
  std::shared_ptr<IQueryEngine> engine_;
};
} // namespace
std::shared_ptr<ICallGraphBackend>
make_call_graph_backend(std::shared_ptr<IQueryEngine> engine) {
  return std::make_shared<CallGraphBackend>(engine ? std::move(engine)
                                                   : make_query_engine());
}
} // namespace ctk::clang_layer
