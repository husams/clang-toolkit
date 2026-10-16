#include "ctk/clang/call_graph_backend.hpp"
#include "../captured_binding_state.hpp"
#include "../native_snapshot_owner.hpp"
#include "../serialization/analysis_projection.hpp"
#include "../serialization/match_metadata_helpers.hpp"
#include "call_graph_builder.hpp"
#include "call_graph_edge.hpp"
#include "call_graph_node.hpp"
#include "ctk/clang/file_discovery.hpp"
#include "declaration_order.hpp"
#include <algorithm>
#include <clang/AST/ParentMapContext.h>
#include <clang/AST/RecursiveASTVisitor.h>
#include <clang/Basic/SourceManager.h>
#include <limits>
#include <optional>
#include <unordered_map>
#include <unordered_set>
namespace ctk::clang_layer {
namespace {
const clang::Decl *enclosing_callable(const clang::Stmt &, clang::ASTContext &);
struct NativeCallSite {
  const clang::CallExpr *call{};
  const clang::Decl *invoking_callable{};
};
class CallSiteCollector final
    : public clang::RecursiveASTVisitor<CallSiteCollector> {
public:
  CallSiteCollector(calls::CallGraphBudget &budget, std::size_t limit,
                    clang::ASTContext &ast, bool main_file_only)
      : budget_(budget), limit_(limit), sources_(ast.getSourceManager()),
        ast_(ast), main_file_only_(main_file_only) {}
  bool TraverseDecl(clang::Decl *decl) {
    // A default argument executes at each invocation, not at its declaration.
    if (llvm::isa_and_nonnull<clang::ParmVarDecl>(decl))
      return true;
    const auto *previous = callable_;
    const auto previous_default = in_default_argument_;
    const auto *previous_invoker = invoking_callable_;
    if (llvm::isa_and_nonnull<clang::FunctionDecl>(decl) ||
        llvm::isa_and_nonnull<clang::BlockDecl>(decl)) {
      callable_ = decl;
      in_default_argument_ = false;
      invoking_callable_ = nullptr;
    }
    const auto result =
        clang::RecursiveASTVisitor<CallSiteCollector>::TraverseDecl(decl);
    callable_ = previous;
    in_default_argument_ = previous_default;
    invoking_callable_ = previous_invoker;
    return result;
  }
  bool TraverseCXXDefaultArgExpr(clang::CXXDefaultArgExpr *expression) {
    const auto previous = in_default_argument_;
    const auto *previous_invoker = invoking_callable_;
    if (!in_default_argument_)
      invoking_callable_ = enclosing_callable(*expression, ast_);
    in_default_argument_ = true;
    const auto result = clang::RecursiveASTVisitor<
        CallSiteCollector>::TraverseCXXDefaultArgExpr(expression);
    in_default_argument_ = previous;
    invoking_callable_ = previous_invoker;
    return result;
  }
  bool VisitCallExpr(clang::CallExpr *call) {
    if (main_file_only_ && !sources_.isWrittenInMainFile(
                               sources_.getExpansionLoc(call->getExprLoc())))
      return true;
    budget_.check();
    if (budget_.call_sites >= limit_)
      throw calls::CallGraphFailure(MatchCode::ResourceExhausted,
                                    "call graph call-site limit exceeded");
    ++budget_.call_sites;
    sites.push_back(
        {call, in_default_argument_
                   ? (invoking_callable_ ? invoking_callable_ : callable_)
                   : nullptr});
    return true;
  }
  bool shouldVisitImplicitCode() const { return visit_implicit_; }
  bool shouldVisitTemplateInstantiations() const { return visit_templates_; }
  void set_visit_flags(bool implicit, bool templates) {
    visit_implicit_ = implicit;
    visit_templates_ = templates;
  }
  std::vector<NativeCallSite> sites;

private:
  calls::CallGraphBudget &budget_;
  std::size_t limit_;
  clang::SourceManager &sources_;
  clang::ASTContext &ast_;
  bool main_file_only_;
  bool visit_implicit_{true};
  bool visit_templates_{true};
  const clang::Decl *callable_{};
  const clang::Decl *invoking_callable_{};
  bool in_default_argument_{false};
};
const clang::Decl *enclosing_callable(const clang::Stmt &call,
                                      clang::ASTContext &ast) {
  std::vector<clang::DynTypedNode> pending{clang::DynTypedNode::create(call)};
  std::vector<clang::DynTypedNode> seen = pending;
  while (!pending.empty()) {
    std::vector<clang::DynTypedNode> next;
    for (const auto &node : pending)
      for (const auto &parent : ast.getParents(node)) {
        if (const auto *function = parent.get<clang::FunctionDecl>())
          return function;
        if (const auto *block = parent.get<clang::BlockDecl>())
          return block;
        if (std::find(seen.begin(), seen.end(), parent) == seen.end() &&
            std::find(next.begin(), next.end(), parent) == next.end()) {
          seen.push_back(parent);
          next.push_back(parent);
        }
      }
    pending = std::move(next);
  }
  return nullptr;
}

const clang::Decl *callable_key(const clang::Decl *decl) {
  if (const auto *function = llvm::dyn_cast_or_null<clang::FunctionDecl>(decl))
    return function->getCanonicalDecl();
  return decl;
}
struct TopologyEdge {
  std::size_t caller, callee;
  const clang::CallGraphNode::CallRecord *record;
};
struct TopologySite {
  std::size_t caller;
  std::optional<std::size_t> callee;
  const clang::CallExpr *call;
};
class CallGraphBackend final : public ICallGraphBackend {
public:
  explicit CallGraphBackend(std::shared_ptr<IQueryEngine> engine)
      : engine_(std::move(engine)) {}
  CallGraphResult build(const ctk::analysis::v1::CallGraphRequest &request,
                        const IMatchBackend::Checkpoint &checkpoint,
                        const CallGraphLimits &limits) override {
    return build_selected(request, {}, checkpoint, limits);
  }
  CallGraphResult
  build_selected(const ctk::analysis::v1::CallGraphRequest &request,
                 std::shared_ptr<const NativeBindingState> previous,
                 const IMatchBackend::Checkpoint &checkpoint,
                 const CallGraphLimits &limits) override {
    CallGraphResult collected;
    std::size_t bytes = 0;
    const auto result = produce(
        request, std::move(previous), checkpoint, limits,
        [&](const ctk::analysis::v1::CallGraphStreamEvent &event,
            std::string &message) {
          // Bound collector growth before publishing its atomic unary result.
          if (event.ByteSizeLong() > limits.max_bytes - bytes) {
            message = "call graph response byte limit exceeded";
            return MatchCode::ResourceExhausted;
          }
          bytes += event.ByteSizeLong();
          if (event.has_graph_started())
            collected.response.CopyFrom(event.graph_started().graph());
          const auto append = [&](const auto &record, auto *destination) {
            destination->CopyFrom(record);
            for (const auto &availability : record.availability())
              collected.response.add_availability()->CopyFrom(availability);
          };
          if (event.has_node())
            append(event.node().node(), collected.response.add_nodes());
          else if (event.has_edge())
            append(event.edge().edge(), collected.response.add_edges());
          else if (event.has_call_site())
            append(event.call_site().call_site(),
                   collected.response.add_call_sites());
          return MatchCode::Ok;
        });
    if (result.code != MatchCode::Ok)
      return {result.code, result.message, {}};
    collected.response.set_is_complete(result.completed.is_complete());
    if (collected.response.ByteSizeLong() > limits.max_bytes)
      return {MatchCode::ResourceExhausted,
              "call graph response byte limit exceeded",
              {}};
    return collected;
  }
  CallGraphStreamResult
  build_stream(const ctk::analysis::v1::CallGraphRequest &request,
               std::shared_ptr<const NativeBindingState> previous,
               const IMatchBackend::Checkpoint &checkpoint,
               const CallGraphLimits &limits, const EventSink &sink) override {
    return produce(request, std::move(previous), checkpoint, limits, sink);
  }

private:
  CallGraphStreamResult
  produce(const ctk::analysis::v1::CallGraphRequest &request,
          std::shared_ptr<const NativeBindingState> previous,
          const IMatchBackend::Checkpoint &checkpoint,
          const CallGraphLimits &limits, const EventSink &sink) {
    CallGraphStreamResult result;
    if (!sink)
      return {
          MatchCode::InvalidArgument, "call graph event sink is required", {}};
    try {
      calls::CallGraphBudget budget{checkpoint, limits};
      budget.limits.max_nodes = std::min<std::size_t>(
          limits.max_nodes,
          request.has_max_nodes() ? request.max_nodes() : 10000);
      budget.limits.max_edges = std::min<std::size_t>(
          limits.max_edges,
          request.has_max_edges() ? request.max_edges() : 100000);
      budget.check();
      ctk::cache::SnapshotPtr snapshot;
      if (request.has_file()) {
        const auto &file = request.file();
        ctk::match::v1::InputDescriptor descriptor;
        descriptor.set_file_path(file.file_path());
        auto *profile = descriptor.mutable_profile();
        profile->set_working_directory(file.working_directory());
        profile->set_compilation_database(file.compilation_database());
        profile->set_frozen(file.frozen_profile());
        profile->set_profile_id(file.expected_profile_id());
        *profile->mutable_compile_arguments() = file.compile_arguments();
        snapshot =
            engine_->acquire_snapshot(resolve_file_descriptor(descriptor).file);
      } else if (previous)
        snapshot = previous->snapshot();
      if (!snapshot)
        return {
            MatchCode::FailedPrecondition, "native snapshot unavailable", {}};
      std::lock_guard lane(snapshot->execution_mutex());
      auto owner =
          std::dynamic_pointer_cast<const AstSnapshotOwner>(snapshot->owner);
      if (!owner || !owner->unit)
        return {MatchCode::Internal, "invalid native snapshot owner", {}};
      auto &ast = owner->unit->getASTContext();
      const clang::Decl *requested_callable = nullptr;
      const clang::CallExpr *requested_call = nullptr;
      if (request.has_binding()) {
        const auto state =
            std::dynamic_pointer_cast<const CapturedBindingState>(previous);
        if (!state)
          return {
              MatchCode::FailedPrecondition, "native bindings unavailable", {}};
        const auto &target = request.binding();
        std::size_t candidates = 0;
        for (std::size_t row = 0; row < state->rows.size(); ++row) {
          budget.check();
          if (target.has_match_index() && row != target.match_index())
            continue;
          const auto found = state->rows[row].find(target.bind());
          if (found == state->rows[row].end())
            continue;
          ++candidates;
          requested_callable = found->second.get<clang::FunctionDecl>();
          requested_call = found->second.get<clang::CallExpr>();
          if (!requested_callable && !requested_call)
            return {
                MatchCode::InvalidArgument,
                "call graph binding must be one callable or call expression",
                {}};
        }
        if (!candidates)
          return {MatchCode::NotFound, "binding or row unavailable", {}};
        if (candidates != 1)
          return {MatchCode::InvalidArgument,
                  "call graph binding must select exactly one match",
                  {}};
        if (requested_call) {
          requested_callable = enclosing_callable(*requested_call, ast);
          if (!requested_callable)
            return {MatchCode::FailedPrecondition,
                    "call expression has no enclosing callable",
                    {}};
        }
        if (const auto *function =
                llvm::dyn_cast_or_null<clang::FunctionDecl>(requested_callable);
            function && function->isDependentContext())
          return {MatchCode::FailedPrecondition,
                  "call graph cannot focus a dependent callable template",
                  {}};
      }
      if (requested_call &&
          (request.direction() !=
               ctk::analysis::v1::CALL_GRAPH_DIRECTION_UNSPECIFIED ||
           request.has_max_depth() || request.unlimited_depth()))
        return {MatchCode::InvalidArgument,
                "direction and depth apply to callable targets, not call "
                "expressions",
                {}};
      calls::CallGraphBuilder graph(budget, request.main_file_only());
      if (request.has_visit_implicit_code())
        graph.ShouldVisitImplicitCode = request.visit_implicit_code();
      if (request.has_visit_template_instantiations())
        graph.ShouldVisitTemplateInstantiations =
            request.visit_template_instantiations();
      graph.addToCallGraph(ast.getTranslationUnitDecl());
      // An exact declaration-only seed can be absent from Clang's ordinary
      // inventory when no represented call references it yet.
      if (requested_callable && !requested_call)
        graph.getOrInsertNode(
            const_cast<clang::Decl *>(callable_key(requested_callable)));
      calls::DeclarationOrder order(budget);
      order.TraverseAST(ast);
      std::vector<const clang::CallGraphNode *> nodes{graph.getRoot()};
      for (const auto &entry : graph) {
        const auto *node = entry.second.get();
        if (node == graph.getRoot())
          continue;
        if (request.main_file_only() && node->getDecl() &&
            !ast.getSourceManager().isWrittenInMainFile(
                ast.getSourceManager().getExpansionLoc(
                    node->getDecl()->getLocation())))
          continue;
        if (!order.ordinals.contains(node->getDecl()->getCanonicalDecl()))
          return {MatchCode::Internal,
                  "call graph declaration missing from native visitor order",
                  {}};
        nodes.push_back(node);
      }
      if (nodes.size() > budget.limits.max_nodes)
        return {
            MatchCode::ResourceExhausted, "call graph node limit exceeded", {}};
      std::sort(nodes.begin() + 1, nodes.end(), [&order](auto *a, auto *b) {
        return order.ordinals.at(a->getDecl()->getCanonicalDecl()) <
               order.ordinals.at(b->getDecl()->getCanonicalDecl());
      });
      std::unordered_map<const clang::CallGraphNode *, std::size_t> indices;
      std::unordered_map<const clang::Decl *, std::size_t> callable_nodes;
      std::optional<std::size_t> focus;
      for (std::size_t i = 0; i < nodes.size(); ++i) {
        budget.check();
        indices.emplace(nodes[i], i);
        const auto *decl = nodes[i]->getDecl();
        if (!decl)
          continue;
        callable_nodes.emplace(callable_key(decl), i);
        const auto *function = llvm::dyn_cast<clang::FunctionDecl>(decl);
        if ((requested_callable &&
             callable_key(decl) == callable_key(requested_callable)) ||
            (!request.function().empty() && function &&
             function->getQualifiedNameAsString() == request.function())) {
          if (focus)
            return {MatchCode::InvalidArgument,
                    "callable selector is ambiguous; use an exact binding",
                    {}};
          focus = i;
        }
      }
      if ((requested_callable || !request.function().empty()) && !focus)
        return {
            MatchCode::NotFound, "callable not found in pinned snapshot", {}};
      if (!focus && (request.direction() !=
                         ctk::analysis::v1::CALL_GRAPH_DIRECTION_UNSPECIFIED ||
                     request.has_max_depth() || request.unlimited_depth()))
        return {MatchCode::InvalidArgument,
                "direction and depth require one exact callable selector",
                {}};
      std::vector<TopologyEdge> edges;
      std::vector<std::vector<std::size_t>> outgoing(nodes.size()),
          incoming(nodes.size());
      std::uint64_t external_edges = 0;
      for (std::size_t caller = 0; caller < nodes.size(); ++caller)
        for (const auto &record : nodes[caller]->callees()) {
          budget.check();
          const auto callee = indices.find(record.Callee);
          if (callee == indices.end()) {
            if (!request.main_file_only())
              return {MatchCode::Internal,
                      "call graph callee missing from graph",
                      {}};
            ++external_edges;
            continue;
          }
          if (++budget.edges > budget.limits.max_edges)
            return {MatchCode::ResourceExhausted,
                    "call graph edge limit exceeded",
                    {}};
          edges.push_back({caller, callee->second, &record});
          if (caller && callee->second) {
            outgoing[caller].push_back(callee->second);
            incoming[callee->second].push_back(caller);
          }
        }
      const auto max_sites =
          request.has_max_call_sites() ? request.max_call_sites() : 100000;
      CallSiteCollector collector(budget, max_sites, ast,
                                  request.main_file_only());
      collector.set_visit_flags(graph.ShouldVisitImplicitCode,
                                graph.ShouldVisitTemplateInstantiations);
      collector.TraverseDecl(ast.getTranslationUnitDecl());
      std::vector<TopologySite> sites;
      std::unordered_map<const clang::Expr *, std::vector<const TopologyEdge *>>
          invocation_edges;
      for (const auto &edge : edges)
        if (edge.record->CallExpr)
          invocation_edges[edge.record->CallExpr].push_back(&edge);
      std::unordered_set<const clang::CallExpr *> seen_sites;
      for (const auto &native : collector.sites) {
        budget.check();
        if (!native.invoking_callable && !seen_sites.insert(native.call).second)
          continue;
        // A default-argument expression can be shared by several invocations.
        // Native edges identify each actual caller more precisely than parents.
        if (const auto found = invocation_edges.find(native.call);
            !native.invoking_callable && found != invocation_edges.end()) {
          for (const auto *edge : found->second) {
            budget.check();
            if (sites.size() >= max_sites)
              return {MatchCode::ResourceExhausted,
                      "call graph call-site limit exceeded",
                      {}};
            sites.push_back({edge->caller, edge->callee, native.call});
          }
          continue;
        }
        std::size_t caller = 0;
        const auto caller_node = callable_nodes.find(callable_key(
            native.invoking_callable ? native.invoking_callable
                                     : enclosing_callable(*native.call, ast)));
        if (caller_node != callable_nodes.end())
          caller = caller_node->second;
        std::optional<std::size_t> callee;
        if (const auto *target = native.call->getDirectCallee()) {
          const auto found = callable_nodes.find(callable_key(target));
          if (found != callable_nodes.end())
            callee = found->second;
        }
        if (sites.size() >= max_sites)
          return {MatchCode::ResourceExhausted,
                  "call graph call-site limit exceeded",
                  {}};
        sites.push_back({caller, callee, native.call});
      }
      auto direction = request.direction();
      if (focus &&
          direction == ctk::analysis::v1::CALL_GRAPH_DIRECTION_UNSPECIFIED)
        direction = ctk::analysis::v1::CALL_GRAPH_DIRECTION_OUT;
      const auto depth_limit = request.unlimited_depth()
                                   ? std::numeric_limits<std::uint64_t>::max()
                                   : request.has_max_depth() ? request.max_depth()
                                                             : 1;
      std::vector<std::int64_t> depth(nodes.size(), -1);
      std::vector<bool> selected(nodes.size(), !focus);
      selected[0] = true;
      if (focus) {
        selected[*focus] = true;
        depth[*focus] = 0;
        if (!requested_call) {
          std::vector<std::size_t> queue{*focus};
          for (std::size_t position = 0; position < queue.size(); ++position) {
            budget.check();
            const auto current = queue[position];
            if (depth[current] >= depth_limit)
              continue;
            const auto visit = [&](const auto &adjacency) {
              for (const auto next : adjacency[current]) {
                budget.check();
                if (depth[next] < 0) {
                  depth[next] = depth[current] + 1;
                  selected[next] = true;
                  queue.push_back(next);
                }
              }
            };
            if (direction != ctk::analysis::v1::CALL_GRAPH_DIRECTION_IN)
              visit(outgoing);
            if (direction != ctk::analysis::v1::CALL_GRAPH_DIRECTION_OUT)
              visit(incoming);
          }
        } else {
          std::size_t matches = 0;
          const TopologySite *exact_site = nullptr;
          for (const auto &site : sites)
            if (site.call == requested_call) {
              ++matches;
              exact_site = &site;
            }
          if (!matches)
            return {MatchCode::NotFound,
                    "bound call expression is outside graph scope",
                    {}};
          if (matches > 1)
            return {MatchCode::InvalidArgument,
                    "call expression has multiple invocation contexts",
                    {}};
          if (!exact_site->caller)
            return {MatchCode::FailedPrecondition,
                    "call expression has no represented enclosing callable",
                    {}};
          selected[*focus] = false;
          focus = exact_site->caller;
          selected[*focus] = true;
          depth[*focus] = 0;
          if (exact_site->callee)
            selected[*exact_site->callee] = true;
        }
      }
      const auto traversed = [&](std::size_t caller, std::size_t callee) {
        const auto within = [&](std::size_t node) {
          return depth[node] >= 0 && depth[node] < depth_limit;
        };
        return (direction != ctk::analysis::v1::CALL_GRAPH_DIRECTION_IN &&
                within(caller)) ||
               (direction != ctk::analysis::v1::CALL_GRAPH_DIRECTION_OUT &&
                within(callee));
      };
      std::vector<std::size_t> emitted_edges, emitted_sites;
      std::uint64_t boundary_edges = 0, boundary_sites = 0;
      for (std::size_t i = 0; i < edges.size(); ++i) {
        budget.check();
        const auto &edge = edges[i];
        const bool emit =
            !focus || (edge.caller && edge.callee && selected[edge.caller] &&
                       selected[edge.callee] &&
                       (requested_call ? edge.record->CallExpr == requested_call
                                       : traversed(edge.caller, edge.callee)));
        if (emit)
          emitted_edges.push_back(i);
        else if (edge.caller && edge.callee &&
                 (selected[edge.caller] || selected[edge.callee]))
          ++boundary_edges;
      }
      for (std::size_t i = 0; i < sites.size(); ++i) {
        budget.check();
        const auto &site = sites[i];
        const bool emit =
            !focus ||
            (requested_call
                 ? site.call == requested_call
                 : selected[site.caller] &&
                       (site.callee
                            ? selected[*site.callee] &&
                                  traversed(site.caller, *site.callee)
                            : direction != ctk::analysis::v1::
                                               CALL_GRAPH_DIRECTION_IN &&
                                  depth[site.caller] >= 0 &&
                                  depth[site.caller] < depth_limit));
        if (emit)
          emitted_sites.push_back(i);
        else if ((site.caller && selected[site.caller]) ||
                 (site.callee && selected[*site.callee]))
          ++boundary_sites;
      }
      std::vector<std::uint64_t> remap(nodes.size(), 0);
      std::uint64_t node_count = 0;
      for (std::size_t i = 0; i < nodes.size(); ++i)
        if (selected[i])
          remap[i] = node_count++;
      const auto emit = [&](ctk::analysis::v1::CallGraphStreamEvent &event) {
        budget.check();
        if (event.ByteSizeLong() > limits.max_bytes) {
          result.code = MatchCode::ResourceExhausted;
          result.message = "call graph stream event byte limit exceeded";
          return false;
        }
        result.code = sink(event, result.message);
        return result.code == MatchCode::Ok;
      };
      ctk::analysis::v1::CallGraphStreamEvent event;
      auto *started = event.mutable_graph_started();
      started->set_snapshot_generation(snapshot->generation);
      auto *header = started->mutable_graph();
      header->set_root_node(0);
      header->set_main_file_only(request.main_file_only());
      header->set_external_edges_omitted(external_edges);
      header->set_snapshot_generation(snapshot->generation);
      const auto main_file = owner->unit->getMainFileName().str();
      header->set_source_file(main_file);
      for (const auto &input : snapshot->inputs)
        if (input.path == main_file) {
          header->set_source_revision(input.content_digest);
          break;
        }
      header->set_compilation_profile_id(snapshot->profile_identity);
      if (focus) {
        header->set_focus_node(remap[*focus]);
        header->set_selection_direction(direction);
        if (request.unlimited_depth())
          header->set_selection_unlimited_depth(true);
        else
          header->set_selection_max_depth(depth_limit);
        header->set_selection_boundary_edges(boundary_edges);
        header->set_selection_boundary_call_sites(boundary_sites);
      }
      if (!emit(event))
        return result;
      bool complete = true;
      for (std::size_t i = 0; i < nodes.size(); ++i) {
        if (!selected[i])
          continue;
        budget.check();
        event.Clear();
        auto *value = event.mutable_node()->mutable_node();
        value->set_node_index(remap[i]);
        serialization::SerializationContext context{ast};
        serialization::apply_projection(request.projection(), context);
        calls::write_node(*nodes[i], *value, context);
        complete = complete && context.complete;
        if (!emit(event))
          return result;
      }
      for (const auto i : emitted_edges) {
        budget.check();
        event.Clear();
        const auto &edge = edges[i];
        auto *value = event.mutable_edge()->mutable_edge();
        value->set_caller_node(remap[edge.caller]);
        value->set_callee_node(remap[edge.callee]);
        value->set_is_virtual_root_edge(edge.caller == 0);
        serialization::SerializationContext context{ast};
        serialization::apply_projection(request.projection(), context);
        calls::write_edge(*edge.record, *value, context);
        complete = complete && context.complete;
        if (!emit(event))
          return result;
      }
      for (const auto i : emitted_sites) {
        budget.check();
        event.Clear();
        const auto &site = sites[i];
        auto *value = event.mutable_call_site()->mutable_call_site();
        value->set_caller_node(remap[site.caller]);
        if (site.callee)
          value->set_callee_node(remap[*site.callee]);
        serialization::SerializationContext context{ast};
        serialization::apply_projection(request.projection(), context);
        serialization::helpers::write_expr(site.call, *value->mutable_call(),
                                           context);
        ctk::match::v1::MatchBinding metadata;
        serialization::helpers::write_match_metadata(
            clang::DynTypedNode::create(*site.call), metadata, context);
        if (metadata.has_location())
          value->mutable_location()->CopyFrom(metadata.location());
        if (metadata.has_range())
          value->mutable_range()->CopyFrom(metadata.range());
        if (metadata.has_call_site())
          value->mutable_facts()->CopyFrom(metadata.call_site());
        // Parent maps describe a shared default argument's declaration context;
        // graph edges describe the function invoking that argument here.
        auto *facts = value->mutable_facts();
        facts->clear_caller_name();
        facts->clear_caller_symbol_identity();
        if (const auto *caller = nodes[site.caller]->getDecl()) {
          ctk::match::v1::MatchBinding caller_metadata;
          serialization::helpers::write_match_metadata(
              clang::DynTypedNode::create(*caller), caller_metadata, context);
          facts->set_caller_symbol_identity(caller_metadata.symbol_identity());
          if (const auto *named = llvm::dyn_cast<clang::NamedDecl>(caller))
            facts->set_caller_name(named->getQualifiedNameAsString());
        }
        value->set_is_complete(context.complete);
        for (const auto &availability : context.availability)
          value->add_availability()->CopyFrom(availability);
        complete = complete && context.complete;
        if (!emit(event))
          return result;
      }
      budget.check();
      result.completed.set_graph_count(1);
      result.completed.set_node_count(node_count);
      result.completed.set_edge_count(emitted_edges.size());
      result.completed.set_call_site_count(emitted_sites.size());
      result.completed.set_is_complete(complete);
      return result;
    } catch (const calls::CallGraphFailure &error) {
      return {error.code, error.what(), {}};
    } catch (const ProfileMismatch &error) {
      return {MatchCode::FailedPrecondition, error.what(), {}};
    } catch (const std::exception &error) {
      return {MatchCode::InvalidArgument, error.what(), {}};
    }
  }
  std::shared_ptr<IQueryEngine> engine_;
};
} // namespace
std::shared_ptr<ICallGraphBackend>
make_call_graph_backend(std::shared_ptr<IQueryEngine> engine) {
  return std::make_shared<CallGraphBackend>(engine ? std::move(engine)
                                                   : make_query_engine());
}
} // namespace ctk::clang_layer
