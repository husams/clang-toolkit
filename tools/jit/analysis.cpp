#include "analysis.hpp"
#include "captured_binding_state.hpp"
#include "ctk/cache/path_policy.hpp"
#include "ctk/clang/call_graph_backend.hpp"
#include "ctk/clang/cfg_backend.hpp"
#include "ctk/clang/tooling.hpp"
#include "ctk/clang/traversal_backend.hpp"
#include "documents.hpp"
#include "filters.hpp"
#include "workspace.hpp"
#include "native_navigation.hpp"
#include "native_snapshot_owner.hpp"
#include "semantic.hpp"
#include "value_access.hpp"

#include <filesystem>
#include <map>

#include <google/protobuf/util/json_util.h>
#include <llvm/ADT/StringExtras.h>
#include <llvm/Support/JSON.h>
#include <llvm/Support/SHA256.h>

namespace ctk::jit {
namespace {

namespace api = ctk::analysis::v1;
namespace match = ctk::match::v1;
namespace pb = google::protobuf;
using clang_layer::CapturedBindingState;
using clang_layer::MatchCode;
using namespace value_access;

struct SnapshotPin {
  ctk::cache::SnapshotPtr snapshot;

  // The snapshot's native owner destroys the AST context with its ASTUnit.
  void operator()(clang::ASTContext*) const {}
};

ctk::cache::SnapshotPtr snapshot(const AstHandle& ast) {
  const auto* pin = std::get_deleter<SnapshotPin>(ast);
  return pin ? pin->snapshot : nullptr;
}

std::shared_ptr<CapturedBindingState> bindings(const AstHandle& ast, const NativeNode* node) {
  auto state = std::make_shared<CapturedBindingState>(snapshot(ast));
  if (node) {
    CapturedBindingState::Row parents;
    if (node->parent)
      parents.try_emplace("selected", *node->parent);
    state->append({{"selected", *node->node}}, std::move(parents));
  }
  return state;
}

class SelectedAst final : public clang_layer::IQueryEngine {
public:
  explicit SelectedAst(ctk::cache::SnapshotPtr snapshot) : selected(std::move(snapshot)) {}

  ctk::cache::SnapshotPtr acquire_snapshot(const clang_layer::FileInput&) override {
    return selected;
  }

  clang_layer::QueryResult match(const clang_layer::FileInput&, const std::string&,
                                 const Checkpoint&, const MatchCallback&) override {
    clang_layer::QueryResult result;
    result.message = "the selected AST adapter handles graph analysis";
    return result;
  }

private:
  ctk::cache::SnapshotPtr selected;
};

template <typename Request> void set_target(Request& request, const NativeNode* selected) {
  if (selected)
    request.mutable_binding()->set_bind("selected");
  else
    request.mutable_session()->set_session_id("local");
}

template <typename Request>
bool parse_options(Values& runtime, Request& request, llvm::StringRef options) {
  const auto status = pb::util::JsonStringToMessage(options.str(), &request);
  if (status.ok())
    return true;
  runtime.fail(status.ToString());
  return false;
}

bool emit_message(Values& runtime, const pb::Message& message) {
  if (auto text = runtime.present("graph", message))
    return emit_text(runtime, *text);
  pb::util::JsonPrintOptions options;
  options.add_whitespace = true;
  options.preserve_proto_field_names = true;
  std::string output;
  const auto status = pb::util::MessageToJsonString(message, &output, options);
  if (!status.ok()) {
    runtime.fail(status.ToString());
    return false;
  }
  return emit_text(runtime, llvm::StringRef(output).rtrim("\n"));
}

template <typename Message> const Value* view(Values& runtime, Message message) {
  return runtime.hold({semantic(std::make_unique<Message>(std::move(message)))});
}

template <typename Result> bool ok(Values& runtime, const Result& result) {
  if (result.code == MatchCode::Ok)
    return true;
  if (runtime.error.empty())
    runtime.fail(result.message);
  return false;
}

const Value* traverse(Values& runtime, const std::shared_ptr<SelectedAst>& engine,
                      const std::shared_ptr<CapturedBindingState>& state,
                      const NativeNode* selected, llvm::StringRef options, bool display) {
  api::TraverseRequest request;
  if (!parse_options(runtime, request, options))
    return nullptr;
  set_target(request, selected);
  auto backend = clang_layer::make_traversal_backend(engine);
  auto result = backend->traverse_stream(request, state, [&] { return runtime.tick(); }, {}, {});
  if (!ok(runtime, result) || (display && !emit_message(runtime, result.response)))
    return nullptr;
  return view(runtime, std::move(result.response));
}

const Value* cfg(Values& runtime, const std::shared_ptr<SelectedAst>& engine,
                 const std::shared_ptr<CapturedBindingState>& state, const NativeNode* selected,
                 const Value* name, llvm::StringRef options, bool display) {
  api::CfgRequest request;
  if (!parse_options(runtime, request, options))
    return nullptr;
  set_target(request, selected);
  if (name) {
    const auto* function = as<std::string>(*name);
    if (!function)
      return runtime.fail("cfg requires an exact qualified function name");
    request.set_function(*function);
  } else if (!selected) {
    return runtime.fail("cfg in requires a retained function binding");
  }
  auto backend = clang_layer::make_cfg_backend(engine);
  clang_layer::ICfgBackend::EventSink sink;
  if (display) {
    sink = [&](const api::CfgStreamEvent& event, std::string&) {
      return emit_message(runtime, event) ? MatchCode::Ok : MatchCode::Internal;
    };
  }
  auto result = backend->build_stream(request, state, [&] { return runtime.tick(); }, {}, sink);
  if (!ok(runtime, result))
    return nullptr;
  if (!display)
    return view(runtime, std::move(result.response));

  api::CfgStreamEvent completion;
  auto* counts = completion.mutable_completed();
  counts->set_graph_count(result.graph_count);
  counts->set_block_count(result.block_count);
  counts->set_element_count(result.element_count);
  return emit_message(runtime, completion) ? view(runtime, std::move(completion)) : nullptr;
}

std::string compact(const api::CallGraphResponse& graph) {
  std::map<std::uint64_t, const api::CallGraphNode*> functions;
  std::map<std::uint64_t, std::size_t> calls;
  std::size_t edges = 0, unresolved = 0;
  for (const auto& node : graph.nodes())
    if (!node.is_virtual_root() && node.node_index() != graph.root_node())
      functions.try_emplace(node.node_index(), &node);
  for (const auto& edge : graph.edges())
    if (!edge.is_virtual_root_edge())
      ++edges;
  for (const auto& site : graph.call_sites()) {
    ++calls[site.caller_node()];
    if (site.has_callee_node())
      continue;
    const auto& facts = site.facts();
    if (!site.has_facts() || facts.dispatch() == match::CALL_DISPATCH_INDIRECT ||
        (facts.dispatch() != match::CALL_DISPATCH_DIRECT &&
         facts.dispatch() != match::CALL_DISPATCH_VIRTUAL &&
         facts.static_callee_symbol_identity().empty() && facts.static_callee_name().empty()))
      ++unresolved;
  }
  std::string result;
  llvm::raw_string_ostream out(result);
  out << "Call graph: " << functions.size() << " functions, " << edges << " calls, "
      << graph.call_sites_size() << " call sites, " << unresolved << " unresolved; "
      << (graph.is_complete() ? "complete" : "partial");
  for (const auto& [index, node] : functions) {
    const auto& function = node->function();
    out << "\n  " << (node->has_function() ? function.qualified_name() : node->declaration_kind());
    if (function.has_type() && !function.type().spelling().empty())
      out << ' ' << function.type().spelling();
    out << " @ ";
    const auto& location = node->location();
    if (location.valid())
      out << location.file() << ':' << location.line() << ':' << location.column();
    else
      out << '?';
    out << ": " << calls[index] << " call sites";
    if (graph.has_focus_node() && graph.focus_node() == index)
      out << " [seed]";
  }
  return result;
}

const Value* callgraph(Values& runtime, const std::shared_ptr<SelectedAst>& engine,
                       const std::shared_ptr<CapturedBindingState>& state,
                       const NativeNode* selected, const AstHandle& ast,
                       api::CallGraphRequest request, bool display, bool json) {
  set_target(request, selected);
  request.set_retain_nodes(!display);
  auto backend = clang_layer::make_call_graph_backend(engine);
  auto result = backend->build_selected(request, state, [&] { return runtime.tick(); }, {});
  if (!ok(runtime, result))
    return nullptr;
  if (display) {
    if (json ? !emit_message(runtime, result.response)
             : !emit_text(runtime, compact(result.response)))
      return nullptr;
  }

  std::vector<std::shared_ptr<NativeNode>> nodes;
  if (const auto native =
          std::dynamic_pointer_cast<const CapturedBindingState>(result.native_nodes.state)) {
    for (const auto& row : native->rows) {
      const auto found = row.find("node");
      if (found == row.end())
        return runtime.fail("call graph retained node is unavailable");
      nodes.push_back(std::make_shared<NativeNode>(
          NativeNode{ast, std::make_shared<clang::DynTypedNode>(found->second), {}, {}, "node"}));
    }
  }
  auto graph = std::make_unique<api::CallGraphResponse>(std::move(result.response));
  return runtime.hold({semantic_graph(std::move(graph), std::move(nodes))});
}

const Value* variable_flow(Values& runtime, const std::shared_ptr<SelectedAst>& engine,
                           const std::shared_ptr<CapturedBindingState>& state,
                           const NativeNode* selected, const Value* function,
                           llvm::StringRef options, bool display) {
  const auto* target = function ? retained_node(*function) : nullptr;
  if (!selected || !target)
    return runtime.fail("variableflow requires retained variable and function bindings");
  api::VariableFlowRequest request;
  if (!parse_options(runtime, request, options))
    return nullptr;
  request.mutable_variable()->set_bind("selected");
  request.mutable_function()->set_bind("selected");
  api::VariableFlowReport report;
  auto backend = clang_layer::make_cfg_backend(engine);
  auto result = backend->variable_flow(
      request, state, bindings(target->ast, target), [&] { return runtime.tick(); }, {},
      [&](const api::VariableFlowEvent& event, std::string&) {
        if (display && !emit_message(runtime, event))
          return MatchCode::Internal;
        switch (event.event_case()) {
        case api::VariableFlowEvent::kStarted:
          *report.mutable_analysis() = event.started();
          break;
        case api::VariableFlowEvent::kUsage:
          *report.add_usages() = event.usage();
          break;
        case api::VariableFlowEvent::kFact:
          *report.add_facts() = event.fact();
          break;
        case api::VariableFlowEvent::kFinding:
          *report.add_findings() = event.finding();
          break;
        case api::VariableFlowEvent::kCompleted:
          *report.mutable_completed() = event.completed();
          break;
        default:
          break;
        }
        return MatchCode::Ok;
      });
  return ok(runtime, result) ? view(runtime, std::move(report)) : nullptr;
}

} // namespace

AstHandle retain_snapshot(ctk::cache::SnapshotPtr snapshot) {
  if (!snapshot)
    return {};
  const auto* owner = dynamic_cast<const clang_layer::AstSnapshotOwner*>(snapshot->owner.get());
  if (!owner || !owner->unit)
    return {};
  return AstHandle(&owner->unit->getASTContext(), SnapshotPin{std::move(snapshot)});
}

AstHandle retain_ast(std::unique_ptr<clang::ASTUnit> unit, std::uint64_t generation) {
  if (!unit)
    return {};
  auto* context = &unit->getASTContext();
  const auto path = ctk::cache::path_key(
      std::filesystem::absolute(unit->getMainFileName().str()).lexically_normal().string());
  const auto& sources = context->getSourceManager();
  const auto text = sources.getBufferData(sources.getMainFileID());
  const auto digest = llvm::toHex(llvm::SHA256::hash(llvm::arrayRefFromStringRef(text)), true);
  auto owner = std::make_shared<clang_layer::AstSnapshotOwner>();
  owner->unit = std::move(unit);
  ctk::cache::LoadedSnapshot loaded;
  loaded.owner = std::move(owner);
  loaded.inputs.push_back({path, ctk::cache::InputKind::File, digest});
  loaded.reusable = false;
  return retain_snapshot(
      std::make_shared<ctk::cache::SnapshotEntry>(generation, "standalone", std::move(loaded)));
}

const Value* select_callgraph(Values& runtime, const NativeNode& target,
                               const api::CallGraphResponse& graph, std::optional<std::uint64_t> depth,
                               bool callers) {
  if (!runtime.accepts_ast(target.ast))
    return runtime.fail("AST is outside the resource scope manifest");
  if (!snapshot(target.ast))
    return runtime.fail("native snapshot unavailable");
  api::CallGraphRequest request;
  request.set_direction(callers ? api::CALL_GRAPH_DIRECTION_IN : api::CALL_GRAPH_DIRECTION_OUT);
  if (depth)
    request.set_max_depth(*depth);
  else
    request.set_unlimited_depth(true);
  request.set_main_file_only(graph.main_file_only());
  request.set_exclude_system_headers(graph.exclude_system_headers());
  request.set_node_filter(graph.node_filter());
  request.set_strict_node_filter(graph.strict_node_filter());
  return callgraph(runtime, std::make_shared<SelectedAst>(snapshot(target.ast)),
                   bindings(target.ast, &target), &target, target.ast, std::move(request),
                   false, false);
}

const Value* analyze(Values& runtime, llvm::StringRef operation, const AstHandle& ast,
                     const NativeNode* selected, const Value* operand, llvm::StringRef options,
                     bool display) {
  if (!snapshot(ast))
    return runtime.fail("native snapshot unavailable");
  auto engine = std::make_shared<SelectedAst>(snapshot(ast));
  auto state = bindings(ast, selected);
  display = display && runtime.consume_depth == 0;
  if (operation == "traverse")
    return traverse(runtime, engine, state, selected, options, display);
  if (operation == "cfg")
    return cfg(runtime, engine, state, selected, operand, options, display);
  if (operation == "variable_flow")
    return variable_flow(runtime, engine, state, selected, operand, options, display);
  if (operation == "callgraph" || operation == "callgraph_json") {
    api::CallGraphRequest request;
    if (!parse_options(runtime, request, options))
      return nullptr;
    return callgraph(runtime, engine, state, selected, ast, std::move(request), display,
                     operation == "callgraph_json");
  }
  return runtime.fail(llvm::Twine("unknown analysis operation: ") + operation);
}

const Value* navigate(Values& runtime, const NativeNode& selected, const MatcherValue* matcher,
                      llvm::StringRef axis, std::uint64_t maximum,
                      std::optional<std::uint64_t> index, bool step, bool display,
                      bool bind_candidate) {
  if (axis != "children" && axis != "parents")
    return runtime.fail("navigation axis must be children or parents");
  match::MatchRequest request;
  request.mutable_binding()->set_bind("selected");
  if (runtime.state.spelled_only)
    request.set_traversal_mode(match::MATCH_TRAVERSAL_MODE_IGNORE_UNLESS_SPELLED_IN_SOURCE);
  request.set_navigation_axis(axis == "children" ? match::NAVIGATION_AXIS_CHILDREN
                                                 : match::NAVIGATION_AXIS_PARENTS);
  if (maximum)
    request.set_navigation_max_nodes(maximum);
  if (matcher)
    request.set_query(matcher->text);
  auto result = clang_layer::navigate_bindings(
      request, bindings(selected.ast, &selected), [&] { return runtime.tick(); }, {}, nullptr,
      bind_candidate);
  if (!ok(runtime, result))
    return nullptr;
  const auto native = std::dynamic_pointer_cast<const CapturedBindingState>(result.state);
  if (!native)
    return runtime.fail("native navigation result is unavailable");

  const auto& result_rows = result.rows;
  auto row = [&](std::size_t ordinal) {
    const auto& values = native->rows[ordinal];
    const auto& parents = native->navigation_parents[ordinal];
    auto result = std::make_shared<Record>();
    result->match_row = true;
    result->source_file = native_source_file(selected.ast);
    if (const auto& wire = result_rows[ordinal]; wire.has_source_match_index())
      result->source_match_index = wire.source_match_index();
    for (const auto& [name, node] : values) {
      auto value = std::make_shared<NativeNode>(
          NativeNode{selected.ast, std::make_shared<clang::DynTypedNode>(node), {}, {}, name,
                     static_cast<std::int64_t>(ordinal)});
      if (const auto found = parents.find(name); found != parents.end())
        value->parent = std::make_shared<clang::DynTypedNode>(found->second);
      result->set(name, {std::move(value)});
    }
    return result;
  };

  if (step) {
    if (!index && native->rows.size() != 1)
      return runtime.fail("step requires exactly one result");
    const auto ordinal = index.value_or(0);
    if (ordinal >= native->rows.size())
      return runtime.fail("navigation index out of range");
    const auto selected = row(ordinal);
    const auto target = selected->fields.find("target");
    if (target == selected->fields.end())
      return runtime.fail("navigation target is unavailable");
    if (display && !runtime.consume_depth &&
        !(runtime.workspace && runtime.workspace->capture(runtime, "print", target->second))) {
      const auto* text = ctk_jit_value_render_v1(&runtime, &target->second);
      if (!text || !emit_text(runtime, *as<std::string>(*text)))
        return nullptr;
    }
    return runtime.hold(target->second);
  }

  std::vector<Value> rows;
  for (std::size_t ordinal = 0; ordinal < native->rows.size(); ++ordinal)
    rows.push_back({row(ordinal)});
  if (display && !emit_text(runtime, std::to_string(rows.size()) + " neighbours"))
    return nullptr;
  return runtime.hold(list(std::move(rows)));
}

} // namespace ctk::jit
