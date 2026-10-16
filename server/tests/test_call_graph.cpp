#include "ctk/application/call_graph_controller.hpp"
#include "ctk/platform/temporary_directory.hpp"
#include <algorithm>
#include <fstream>
#include <gtest/gtest.h>
#include <map>
#include <set>
#include <tuple>
#include <vector>
namespace ctk::application {
namespace {
using ctk::clang_layer::MatchCode;
class CallGraph : public ::testing::Test {
protected:
  ctk::platform::TemporaryDirectory directory{"ctk-call-graph"};
  CallGraphController controller;
  ctk::analysis::v1::CallGraphRequest request;
  void SetUp() override {
    std::ofstream(directory.path() / "fixture.cc") << R"cpp(
int external(int);
int leaf(int x){return x;}
int recursive(int n){return n?recursive(n-1):0;}
int twice(){ return leaf(7)+leaf(8)+external(9); }
struct Base { virtual int run(){return 1;} virtual ~Base(){} };
struct Derived:Base { int run() override {return leaf(3);} };
int virtual_call(Base& b){return b.run();}
int indirect(){auto fn=&leaf;return fn(5);}
template<class T> int id(T x){return leaf(x);}
int instantiations(){return id(4);}
int lambda(){return []{return leaf(2);}();}
)cpp";
    request.mutable_file()->set_file_path("fixture.cc");
    request.mutable_file()->set_working_directory(directory.path().string());
    request.mutable_file()->add_compile_arguments("-std=c++20");
  }
};
TEST_F(CallGraph,
       NativeRecordsPreserveRepeatedCallsRecursionAndDeclaredCallees) {
  auto result = controller.build(request, [] { return true; });
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  const auto &response = result.response;
  ASSERT_GT(response.nodes_size(), 8);
  EXPECT_EQ(response.root_node(), 0U);
  EXPECT_TRUE(response.nodes(0).is_virtual_root());
  std::map<std::string, std::uint64_t> nodes;
  for (int i = 0; i < response.nodes_size(); ++i) {
    const auto &node = response.nodes(i);
    EXPECT_EQ(node.node_index(), static_cast<std::uint64_t>(i));
    if (node.has_function())
      nodes.emplace(node.function().qualified_name(), node.node_index());
  }
  ASSERT_TRUE(nodes.contains("twice"));
  ASSERT_TRUE(nodes.contains("leaf"));
  ASSERT_TRUE(nodes.contains("external"));
  EXPECT_FALSE(response.nodes(nodes.at("external")).has_definition());
  EXPECT_TRUE(response.nodes(nodes.at("leaf")).has_definition());
  int repeated = 0, recursive = 0;
  for (const auto &edge : response.edges()) {
    EXPECT_LT(edge.caller_node(),
              static_cast<std::uint64_t>(response.nodes_size()));
    EXPECT_LT(edge.callee_node(),
              static_cast<std::uint64_t>(response.nodes_size()));
    EXPECT_EQ(edge.is_virtual_root_edge(), edge.caller_node() == 0);
    if (edge.is_virtual_root_edge())
      EXPECT_FALSE(edge.has_call());
    if (edge.caller_node() == nodes.at("twice") &&
        edge.callee_node() == nodes.at("leaf")) {
      ++repeated;
      ASSERT_TRUE(edge.has_call());
      EXPECT_TRUE(edge.call().has_call_expr());
      EXPECT_EQ(edge.call().call_expr().call().direct_callee().qualified_name(),
                "leaf");
    }
    if (edge.caller_node() == nodes.at("recursive") &&
        edge.callee_node() == nodes.at("recursive"))
      ++recursive;
  }
  EXPECT_EQ(repeated, 2);
  EXPECT_EQ(recursive, 1);
  const auto owned = response.SerializeAsString();
  std::filesystem::remove(directory.path() / "fixture.cc");
  EXPECT_EQ(response.SerializeAsString(), owned);
}
TEST_F(CallGraph, NativeStaticDispatchAndIndirectCallLimitsAreHonest) {
  auto result = controller.build(request, [] { return true; });
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  std::map<std::string, std::uint64_t> nodes;
  for (const auto &node : result.response.nodes())
    if (node.has_function())
      nodes.emplace(node.function().qualified_name(), node.node_index());
  bool static_callee = false, invented_indirect = false;
  for (const auto &edge : result.response.edges()) {
    if (edge.caller_node() == nodes.at("virtual_call")) {
      static_callee |= result.response.nodes(edge.callee_node())
                           .function()
                           .qualified_name() == "Base::run";
      EXPECT_NE(
          result.response.nodes(edge.callee_node()).function().qualified_name(),
          "Derived::run");
    }
    invented_indirect |= edge.caller_node() == nodes.at("indirect");
  }
  EXPECT_TRUE(static_callee);
  EXPECT_FALSE(invented_indirect);
  int indirect_sites = 0;
  bool method_site_has_method_caller = false;
  for (const auto &site : result.response.call_sites())
    if (site.has_facts() &&
        site.facts().caller_name() == "indirect" &&
        site.facts().dispatch() == ctk::match::v1::CALL_DISPATCH_INDIRECT) {
      ++indirect_sites;
      EXPECT_FALSE(site.has_callee_node());
      EXPECT_TRUE(site.location().valid());
    }
  for (const auto &site : result.response.call_sites())
    if (site.has_callee_node() &&
        site.callee_node() == nodes.at("leaf") &&
        site.caller_node() <
            static_cast<std::uint64_t>(result.response.nodes_size()))
      method_site_has_method_caller |=
          result.response.nodes(site.caller_node()).has_function() &&
          result.response.nodes(site.caller_node())
                  .function()
                  .qualified_name() == "Derived::run";
  EXPECT_EQ(indirect_sites, 1);
  EXPECT_TRUE(method_site_has_method_caller);
}
TEST_F(CallGraph, DefaultArgumentSitesRetainEachCallingFunction) {
  std::ofstream(directory.path() / "defaults.cc")
      << "void leaf(){}\n"
         "int sink(int value=(leaf(),1)){return value;}\n"
         "void first(){sink();} void second(){sink();}\n"
         "void (*callback)();\n"
         "int indirect_sink(int value=(callback(),1)){return value;}\n"
         "void first_indirect(){indirect_sink();} "
         "void second_indirect(){indirect_sink();}\n"
         "int outer(int value=(leaf(),1)){return value;}\n"
         "int nested(int value=(outer(),2)){return value;}\n"
         "void first_nested(){nested();} void second_nested(){nested();}\n"
         "int lambda_default(int value = []{leaf(); return 1;}()){return value;}\n"
         "void first_lambda(){lambda_default();}\n";
  request.mutable_file()->set_file_path("defaults.cc");
  const auto result = controller.build(request, [] { return true; });
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  std::map<std::uint64_t, std::string> names;
  for (const auto &node : result.response.nodes())
    if (node.has_function())
      names.emplace(node.node_index(), node.function().qualified_name());
  std::set<std::string> callers;
  std::set<std::string> indirect_callers;
  std::set<std::string> nested_callers;
  std::set<std::string> all_leaf_callers;
  bool lambda_body_retains_lambda_caller = false;
  for (const auto &site : result.response.call_sites())
    if (site.has_facts()) {
      if (site.facts().dispatch() == ctk::match::v1::CALL_DISPATCH_DIRECT &&
          site.facts().static_callee_name() == "leaf") {
        const auto &caller = names[site.caller_node()];
        all_leaf_callers.insert(caller);
        if (caller == "first" || caller == "second")
          callers.insert(caller);
        if (caller == "first_nested" || caller == "second_nested")
          nested_callers.insert(caller);
        if (caller.find("operator()") != std::string::npos &&
            caller != "first_lambda")
          lambda_body_retains_lambda_caller = true;
      }
      if (site.facts().dispatch() == ctk::match::v1::CALL_DISPATCH_INDIRECT &&
          site.location().valid())
        indirect_callers.insert(names[site.caller_node()]);
    }
  EXPECT_EQ(callers, (std::set<std::string>{"first", "second"}));
  EXPECT_EQ(indirect_callers,
            (std::set<std::string>{"first_indirect", "second_indirect"}));
  EXPECT_EQ(nested_callers,
            (std::set<std::string>{"first_nested", "second_nested"}));
  EXPECT_TRUE(lambda_body_retains_lambda_caller)
      << "leaf callsite callers: " << testing::PrintToString(all_leaf_callers);
}
TEST_F(CallGraph, ExactCallableSelectionDefaultsToOneOutgoingLevel) {
  request.set_function("twice");
  request.set_max_depth(1);
  auto result = controller.build(request, [] { return true; });
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  const auto &response = result.response;
  EXPECT_EQ(response.source_file(),
            (directory.path() / "fixture.cc").string());
  EXPECT_GT(response.snapshot_generation(), 0U);
  EXPECT_FALSE(response.compilation_profile_id().empty());
  ASSERT_TRUE(response.has_focus_node());
  ASSERT_LT(response.focus_node(),
            static_cast<std::uint64_t>(response.nodes_size()));
  EXPECT_EQ(response.nodes(response.focus_node()).function().qualified_name(),
            "twice");
  EXPECT_EQ(response.selection_direction(),
            ctk::analysis::v1::CALL_GRAPH_DIRECTION_OUT);
  EXPECT_EQ(response.selection_max_depth(), 1U);
  EXPECT_EQ(response.nodes(0).is_virtual_root(), true);
  EXPECT_TRUE(response.edges().empty() == false);
  EXPECT_EQ(response.call_sites_size(), 3);
  for (const auto &node : response.nodes())
    if (node.has_function()) {
      EXPECT_FALSE(node.symbol_identity().empty());
      EXPECT_TRUE(node.location().valid());
    }
}
TEST_F(CallGraph, IncomingDepthZeroAndAmbiguousSelectorsAreExplicit) {
  std::ofstream(directory.path() / "direction.cc")
      << "int later(){return 1;} int before(){return later();} "
         "int next(){return later();}\n";
  request.mutable_file()->set_file_path("direction.cc");
  request.set_function("later");
  request.set_direction(ctk::analysis::v1::CALL_GRAPH_DIRECTION_IN);
  request.set_max_depth(1);
  auto incoming = controller.build(request, [] { return true; });
  ASSERT_EQ(incoming.code, MatchCode::Ok) << incoming.message;
  const auto &graph = incoming.response;
  ASSERT_TRUE(graph.has_focus_node());
  EXPECT_EQ(graph.nodes(graph.focus_node()).function().qualified_name(),
            "later");
  std::set<std::string> names;
  for (const auto &node : graph.nodes())
    if (node.has_function())
      names.insert(node.function().qualified_name());
  EXPECT_TRUE(names.contains("before"));
  EXPECT_TRUE(names.contains("next"));
  EXPECT_EQ(graph.call_sites_size(), 2);

  request.set_max_depth(0);
  auto zero = controller.build(request, [] { return true; });
  ASSERT_EQ(zero.code, MatchCode::Ok) << zero.message;
  EXPECT_EQ(zero.response.edges_size(), 0);
  EXPECT_EQ(zero.response.call_sites_size(), 0);
  EXPECT_EQ(zero.response.selection_boundary_call_sites(), 2U);

  request.set_function("missing");
  EXPECT_EQ(controller.build(request, [] { return true; }).code,
            MatchCode::NotFound);
}
TEST_F(CallGraph, UnlimitedDepthReachesLongCyclesAndRejectsConflictingDepth) {
  std::ofstream source(directory.path() / "deep.cc");
  for (int index = 0; index < 40; ++index)
    source << "void f" << index << "();\n";
  for (int index = 0; index < 40; ++index) {
    source << "void f" << index << "() { ";
    if (index < 39)
      source << "f" << index + 1 << "(); ";
    else
      source << "f1(); ";
    if (index == 0)
      source << "f1(); ";
    source << "}\n";
  }
  source << "void disconnected() {}\n";
  source.close();
  request.mutable_file()->set_file_path("deep.cc");
  request.set_function("f0");

  request.set_max_depth(1);
  auto shallow = controller.build(request, [] { return true; });
  ASSERT_EQ(shallow.code, MatchCode::Ok) << shallow.message;
  EXPECT_EQ(shallow.response.nodes_size(), 3);
  EXPECT_EQ(shallow.response.edges_size(), 2);
  EXPECT_EQ(shallow.response.selection_max_depth(), 1U);

  request.set_max_depth(32);
  auto bounded = controller.build(request, [] { return true; });
  ASSERT_EQ(bounded.code, MatchCode::Ok) << bounded.message;
  EXPECT_EQ(bounded.response.nodes_size(), 34);
  EXPECT_EQ(bounded.response.edges_size(), 33);
  EXPECT_EQ(bounded.response.selection_max_depth(), 32U);

  request.clear_max_depth();
  request.set_unlimited_depth(true);
  auto complete = controller.build(request, [] { return true; });
  ASSERT_EQ(complete.code, MatchCode::Ok) << complete.message;
  EXPECT_TRUE(complete.response.has_selection_unlimited_depth());
  EXPECT_TRUE(complete.response.selection_unlimited_depth());
  EXPECT_FALSE(complete.response.has_selection_max_depth());
  EXPECT_EQ(complete.response.nodes_size(), 41);
  EXPECT_EQ(complete.response.edges_size(), 41);
  EXPECT_EQ(complete.response.call_sites_size(), 41);
  int repeated = 0;
  bool disconnected = false;
  for (const auto &node : complete.response.nodes())
    disconnected |= node.has_function() &&
                    node.function().qualified_name() == "disconnected";
  for (const auto &edge : complete.response.edges())
    repeated += edge.caller_node() == complete.response.focus_node() &&
                complete.response.nodes(edge.callee_node())
                        .function()
                        .qualified_name() == "f1";
  EXPECT_EQ(repeated, 2);
  EXPECT_FALSE(disconnected);

  request.set_max_depth(1);
  EXPECT_EQ(controller.build(request, [] { return true; }).code,
            MatchCode::InvalidArgument);
}
TEST_F(CallGraph, FrozenProfileMismatchFailsBeforePublishingGraph) {
  request.mutable_file()->set_expected_profile_id("stale-profile");
  const auto result = controller.build(request, [] { return true; });
  EXPECT_EQ(result.code, MatchCode::FailedPrecondition);
  EXPECT_TRUE(result.response.nodes().empty());
}
TEST_F(CallGraph, StreamRecordsReconstructUnaryAvailabilityAndStayChunked) {
  request.mutable_projection()->set_mode(
      ctk::analysis::v1::ValueProjection::SHALLOW);
  const auto unary = controller.build(request, [] { return true; });
  ASSERT_EQ(unary.code, MatchCode::Ok) << unary.message;
  ctk::analysis::v1::CallGraphResponse collected;
  std::size_t total_event_bytes = 0;
  const auto streamed = controller.build_stream(
      request, [] { return true; },
      [&](const ctk::analysis::v1::CallGraphStreamEvent &event,
          std::string &) {
        EXPECT_LT(event.ByteSizeLong(), 4096U);
        total_event_bytes += event.ByteSizeLong();
        if (event.has_graph_started())
          collected.CopyFrom(event.graph_started().graph());
        else if (event.has_node()) {
          const auto &node = event.node().node();
          collected.add_nodes()->CopyFrom(node);
          for (const auto &field : node.availability())
            collected.add_availability()->CopyFrom(field);
        } else if (event.has_edge()) {
          const auto &edge = event.edge().edge();
          collected.add_edges()->CopyFrom(edge);
          for (const auto &field : edge.availability())
            collected.add_availability()->CopyFrom(field);
        } else if (event.has_call_site()) {
          const auto &site = event.call_site().call_site();
          collected.add_call_sites()->CopyFrom(site);
          for (const auto &field : site.availability())
            collected.add_availability()->CopyFrom(field);
        }
        return MatchCode::Ok;
      });
  ASSERT_EQ(streamed.code, MatchCode::Ok) << streamed.message;
  EXPECT_EQ(streamed.completed.graph_count(), 1U);
  EXPECT_EQ(streamed.completed.node_count(), unary.response.nodes_size());
  EXPECT_EQ(streamed.completed.edge_count(), unary.response.edges_size());
  EXPECT_EQ(streamed.completed.call_site_count(),
            unary.response.call_sites_size());
  collected.set_is_complete(streamed.completed.is_complete());
  EXPECT_EQ(collected.SerializeAsString(), unary.response.SerializeAsString());
  EXPECT_GT(total_event_bytes, 4096U);
}
TEST_F(CallGraph, ProjectionAndMainFileScopeAreExplicitAndComplete) {
  std::ofstream(directory.path() / "external.hpp")
      << "inline int header_only(int value) { return value + 1; }\n";
  std::ofstream(directory.path() / "main_scope.cc")
      << "#include \"external.hpp\"\n"
         "int main_only(int value) { return header_only(value); }\n";
  request.mutable_file()->set_file_path("main_scope.cc");
  request.mutable_file()->add_compile_arguments(
      "-I" + directory.path().string());

  auto shallow_request = request;
  shallow_request.mutable_projection()->set_mode(
      ctk::analysis::v1::ValueProjection::SHALLOW);
  auto shallow = controller.build(shallow_request, [] { return true; });
  ASSERT_EQ(shallow.code, MatchCode::Ok) << shallow.message;
  auto recursive_request = request;
  recursive_request.mutable_projection()->set_mode(
      ctk::analysis::v1::ValueProjection::RECURSIVE);
  auto recursive = controller.build(recursive_request, [] { return true; });
  ASSERT_EQ(recursive.code, MatchCode::Ok) << recursive.message;
  EXPECT_EQ(shallow.response.nodes_size(), recursive.response.nodes_size());
  EXPECT_EQ(shallow.response.edges_size(), recursive.response.edges_size());
  EXPECT_GT(recursive.response.ByteSizeLong(), shallow.response.ByteSizeLong());

  auto invalid = request;
  invalid.mutable_projection()->set_max_depth(0);
  EXPECT_EQ(controller.build(invalid, [] { return true; }).code,
            MatchCode::InvalidArgument);

  request.set_main_file_only(true);
  auto main_only = controller.build(request, [] { return true; });
  ASSERT_EQ(main_only.code, MatchCode::Ok) << main_only.message;
  EXPECT_TRUE(main_only.response.is_complete());
  EXPECT_TRUE(main_only.response.main_file_only());
  EXPECT_GT(main_only.response.external_edges_omitted(), 0U);
  for (const auto &node : main_only.response.nodes())
    if (node.has_function())
      EXPECT_NE(node.function().qualified_name(), "header_only");
}
TEST_F(CallGraph, ScopeFiltersAreAppliedBeforeTopologyAndEchoedInHeader) {
  std::ofstream(directory.path() / "user_extra.hpp")
      << "inline int user_header() { return 2; }\n";
  std::ofstream(directory.path() / "scope.hpp")
      << "#pragma GCC system_header\n"
         "inline int system_leaf() { return 1; }\n"
         "inline int bridge() { return system_leaf(); }\n";
  std::ofstream(directory.path() / "scope.cc")
      << "#include \"scope.hpp\"\n"
         "#include \"user_extra.hpp\"\n"
         "namespace vendor { int trace() { return 3; } }\n"
         "int entry() { return bridge(); }\n"
         "int helper() { return user_header(); }\n"
         "int vendor_entry() { return vendor::trace(); }\n"
         "int rejected() { return system_leaf(); }\n";
  request.mutable_file()->set_file_path("scope.cc");
  request.mutable_file()->add_compile_arguments("-I" +
                                                directory.path().string());
  auto full = controller.build(request, [] { return true; });
  ASSERT_EQ(full.code, MatchCode::Ok) << full.message;
  EXPECT_FALSE(full.response.exclude_system_headers());
  EXPECT_TRUE(full.response.node_filter().empty());
  auto filtered_request = request;
  filtered_request.set_exclude_system_headers(true);
  auto filtered = controller.build(filtered_request, [] { return true; });
  ASSERT_EQ(filtered.code, MatchCode::Ok) << filtered.message;
  EXPECT_TRUE(filtered.response.exclude_system_headers());
  EXPECT_GT(filtered.response.external_edges_omitted(), 0U);
  std::set<std::string> names;
  for (const auto &node : filtered.response.nodes())
    if (node.has_function())
      names.insert(node.function().qualified_name());
  EXPECT_TRUE(names.contains("entry"));
  EXPECT_TRUE(names.contains("helper"));
  EXPECT_TRUE(names.contains("user_header"));
  EXPECT_FALSE(names.contains("system_leaf"));
  EXPECT_FALSE(names.contains("bridge"));
  bool retained_header_boundary_site = false;
  for (const auto &site : filtered.response.call_sites())
    if (site.has_facts() && site.facts().caller_name() == "entry" &&
        site.facts().static_callee_name() == "bridge") {
      retained_header_boundary_site = true;
      EXPECT_FALSE(site.has_callee_node());
    }
  EXPECT_TRUE(retained_header_boundary_site);

  auto custom_request = request;
  custom_request.set_node_filter("functionDecl(unless(hasName(\"rejected\")))");
  auto custom = controller.build(custom_request, [] { return true; });
  ASSERT_EQ(custom.code, MatchCode::Ok) << custom.message;
  EXPECT_EQ(custom.response.node_filter(), custom_request.node_filter());
  for (const auto &node : custom.response.nodes())
    if (node.has_function())
      EXPECT_NE(node.function().qualified_name(), "rejected");
  for (const auto &site : custom.response.call_sites())
    if (site.has_facts())
      EXPECT_NE(site.facts().caller_name(), "rejected")
          << "excluded caller sites cannot be relabeled as root sites";

  auto qualified_request = request;
  qualified_request.set_node_filter(
      "functionDecl(unless(matchesName(\"(^|::)vendor::\")))");
  const auto qualified =
      controller.build(qualified_request, [] { return true; });
  ASSERT_EQ(qualified.code, MatchCode::Ok) << qualified.message;
  bool qualified_boundary_site = false;
  for (const auto &node : qualified.response.nodes())
    if (node.has_function())
      EXPECT_NE(node.function().qualified_name(), "vendor::trace");
  for (const auto &site : qualified.response.call_sites())
    if (site.has_facts() && site.facts().caller_name() == "vendor_entry" &&
        site.facts().static_callee_name() == "vendor::trace") {
      qualified_boundary_site = true;
      EXPECT_FALSE(site.has_callee_node());
    }
  EXPECT_TRUE(qualified_boundary_site);

  auto nested_binding_request = request;
  nested_binding_request.set_node_filter(
      "functionDecl(hasDescendant(callExpr().bind(\"root\")))");
  const auto nested_binding =
      controller.build(nested_binding_request, [] { return true; });
  ASSERT_EQ(nested_binding.code, MatchCode::Ok) << nested_binding.message;
  EXPECT_TRUE(std::any_of(nested_binding.response.nodes().begin(),
                          nested_binding.response.nodes().end(),
                          [](const auto &node) {
                            return node.has_function() &&
                                   node.function().qualified_name() == "entry";
                          }));

  auto narrow_request = request;
  narrow_request.set_main_file_only(true);
  narrow_request.set_exclude_system_headers(true);
  narrow_request.set_node_filter(
      "functionDecl(isExpansionInMainFile(), isDefinition(), "
      "hasName(\"entry\"))");
  narrow_request.set_max_nodes(2);
  narrow_request.set_max_call_sites(1);
  const auto narrow = controller.build(narrow_request, [] { return true; });
  ASSERT_EQ(narrow.code, MatchCode::Ok) << narrow.message;
  ASSERT_EQ(narrow.response.nodes_size(), 2);
  EXPECT_EQ(narrow.response.call_sites_size(), 1);
  EXPECT_EQ(narrow.response.nodes(1).function().qualified_name(), "entry");

  auto invalid = request;
  invalid.set_node_filter("stmt()");
  EXPECT_EQ(controller.build(invalid, [] { return true; }).code,
            MatchCode::InvalidArgument);
  invalid.set_node_filter("functionDecl(");
  EXPECT_EQ(controller.build(invalid, [] { return true; }).code,
            MatchCode::InvalidArgument);
  std::size_t events = 0;
  const auto invalid_stream = controller.build_stream(
      invalid, [] { return true; },
      [&](const ctk::analysis::v1::CallGraphStreamEvent &, std::string &) {
        ++events;
        return MatchCode::Ok;
      });
  EXPECT_EQ(invalid_stream.code, MatchCode::InvalidArgument);
  EXPECT_EQ(events, 0U);
}
TEST_F(CallGraph, CancellationDuringFilteredInventoryPublishesNoEvents) {
  auto source = std::ofstream(directory.path() / "many.cc");
  for (int index = 0; index < 200; ++index)
    source << "int function_" << index << "() { return " << index << "; }\n";
  source.close();
  request.mutable_file()->set_file_path("many.cc");
  request.set_node_filter("functionDecl(unless(hasName(\"never_matches\")))");
  std::size_t checks = 0;
  std::size_t events = 0;
  const auto result = controller.build_stream(
      request, [&] { return ++checks < 700; },
      [&](const ctk::analysis::v1::CallGraphStreamEvent &, std::string &) {
        ++events;
        return MatchCode::Ok;
      });
  EXPECT_EQ(result.code, MatchCode::Cancelled);
  EXPECT_EQ(events, 0U);
}
TEST_F(CallGraph, HeaderVaListImplicitConstructorDoesNotBreakFullScopeGraph) {
  std::ofstream(directory.path() / "va_list.hpp")
      << "namespace demo { inline void copyVaList(__builtin_va_list) {} "
         "inline void chargeCard() { __builtin_va_list arguments; "
         "copyVaList(arguments); } }\n";
  std::ofstream(directory.path() / "va_list.cc")
      << "#include \"va_list.hpp\"\n"
         "void entry() { demo::chargeCard(); }\n";
  request.mutable_file()->set_file_path("va_list.cc");
  const auto add_compile_arguments = [this](const std::string &target) {
    request.mutable_file()->clear_compile_arguments();
    request.mutable_file()->add_compile_arguments("-std=c++20");
    request.mutable_file()->add_compile_arguments(
        "-I" + directory.path().string());
    request.mutable_file()->add_compile_arguments("--target=" + target);
  };
  for (const auto &[target, constructor, expected_constructors] :
       {std::tuple{"x86_64-unknown-linux-gnu",
                   "__va_list_tag::__va_list_tag", 1},
        std::tuple{"aarch64-unknown-linux-gnu", "std::__va_list::__va_list",
                   2},
        std::tuple{"armv7-unknown-linux-gnueabihf",
                   "std::__va_list::__va_list", 2}}) {
    SCOPED_TRACE(target);
    add_compile_arguments(target);
    request.set_main_file_only(false);
    const auto result = controller.build(request, [] { return true; });
    ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
    const auto repeated = controller.build(request, [] { return true; });
    ASSERT_EQ(repeated.code, MatchCode::Ok) << repeated.message;
    EXPECT_EQ(result.response.SerializeAsString(),
              repeated.response.SerializeAsString());

    std::set<std::string> names;
    std::map<std::string, std::vector<std::uint64_t>> node_indices;
    for (const auto &node : result.response.nodes())
      if (node.has_function()) {
        names.insert(node.function().qualified_name());
        node_indices[node.function().qualified_name()].push_back(
            node.node_index());
      }
    EXPECT_TRUE(names.contains("entry"));
    EXPECT_TRUE(names.contains("demo::chargeCard"));
    ASSERT_TRUE(node_indices.contains(constructor));
    ASSERT_GE(node_indices.at(constructor).size(),
              static_cast<std::size_t>(expected_constructors));
    std::size_t va_list_constructor_edges = 0;
    for (const auto &edge : result.response.edges())
      if (edge.caller_node() == node_indices.at("demo::chargeCard").front() &&
          std::find(node_indices.at(constructor).begin(),
                    node_indices.at(constructor).end(),
                    edge.callee_node()) != node_indices.at(constructor).end())
        ++va_list_constructor_edges;
    EXPECT_GE(va_list_constructor_edges,
              static_cast<std::size_t>(expected_constructors));

    request.set_main_file_only(true);
    const auto main_file = controller.build(request, [] { return true; });
    ASSERT_EQ(main_file.code, MatchCode::Ok) << main_file.message;
    EXPECT_TRUE(main_file.response.is_complete());
    EXPECT_GT(main_file.response.external_edges_omitted(), 0U);
    for (const auto &node : main_file.response.nodes())
      if (node.has_function()) {
        EXPECT_NE(node.function().qualified_name(), constructor);
        EXPECT_NE(node.function().qualified_name(), "demo::chargeCard");
      }
  }
}
TEST_F(CallGraph, VisitorFlagsKeepCalleeDoorInstantiationsAndStableIndices) {
  auto baseline = controller.build(request, [] { return true; });
  ASSERT_EQ(baseline.code, MatchCode::Ok) << baseline.message;
  auto repeated = controller.build(request, [] { return true; });
  ASSERT_EQ(repeated.code, MatchCode::Ok);
  EXPECT_EQ(baseline.response.SerializeAsString(),
            repeated.response.SerializeAsString());
  request.set_visit_template_instantiations(false);
  auto uninstantiated = controller.build(request, [] { return true; });
  ASSERT_EQ(uninstantiated.code, MatchCode::Ok) << uninstantiated.message;
  EXPECT_LT(uninstantiated.response.edges_size(),
            baseline.response.edges_size());
  bool id = false;
  for (const auto &node : uninstantiated.response.nodes())
    id |= node.has_function() && node.function().qualified_name() == "id";
  EXPECT_TRUE(id);
  request.set_visit_implicit_code(false);
  auto explicit_only = controller.build(request, [] { return true; });
  ASSERT_EQ(explicit_only.code, MatchCode::Ok) << explicit_only.message;
  EXPECT_LE(explicit_only.response.nodes_size(),
            uninstantiated.response.nodes_size());
}
TEST_F(CallGraph, EmptyTranslationUnitStillHasNativeRoot) {
  std::ofstream(directory.path() / "empty.cc") << "int variable=7;";
  request.mutable_file()->set_file_path("empty.cc");
  request.set_max_nodes(1);
  auto result = controller.build(request, [] { return true; });
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  ASSERT_EQ(result.response.nodes_size(), 1);
  EXPECT_TRUE(result.response.nodes(0).is_virtual_root());
  EXPECT_TRUE(result.response.edges().empty());
}
TEST_F(CallGraph, NodeLimitAcceptsLargerValuesAndExplicitUnlimited) {
  request.set_max_nodes(100001);
  auto large = controller.build(request, [] { return true; });
  ASSERT_EQ(large.code, MatchCode::Ok) << large.message;
  request.set_max_nodes(0);
  auto unlimited = controller.build(request, [] { return true; });
  ASSERT_EQ(unlimited.code, MatchCode::Ok) << unlimited.message;
  EXPECT_EQ(unlimited.response.nodes_size(), large.response.nodes_size());
  std::size_t streamed_nodes = 0;
  auto streamed = controller.build_stream(
      request, [] { return true; },
      [&](const auto &event, std::string &) {
        streamed_nodes += event.has_node();
        return MatchCode::Ok;
      });
  ASSERT_EQ(streamed.code, MatchCode::Ok) << streamed.message;
  EXPECT_EQ(streamed_nodes, unlimited.response.nodes_size());
  request.set_max_nodes(1);
  const auto bounded = controller.build(request, [] { return true; });
  EXPECT_EQ(bounded.code, MatchCode::ResourceExhausted);
  EXPECT_TRUE(bounded.response.nodes().empty());
}
TEST_F(CallGraph, NodeLimitUsesConfiguredDefaultAndRequestOverrides) {
  CursorSettings settings;
  settings.call_graph_default_max_nodes = 1;
  CallGraphController bounded(settings);
  EXPECT_EQ(bounded.build(request, [] { return true; }).code,
            MatchCode::ResourceExhausted);
  request.set_max_nodes(100001);
  EXPECT_EQ(bounded.build(request, [] { return true; }).code, MatchCode::Ok);
  request.set_max_nodes(0);
  EXPECT_EQ(bounded.build(request, [] { return true; }).code, MatchCode::Ok);
  settings.call_graph_default_max_nodes = 0;
  CallGraphController unlimited(settings);
  request.clear_max_nodes();
  const auto result = unlimited.build(request, [] { return true; });
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  EXPECT_GT(result.response.nodes_size(), 1);
  request.set_max_nodes(1);
  EXPECT_EQ(unlimited.build(request, [] { return true; }).code,
            MatchCode::ResourceExhausted);
}
TEST_F(CallGraph, StreamsMoreThanOneHundredThousandNodes) {
  constexpr std::size_t functions = 100001;
  {
    std::ofstream source(directory.path() / "large.cc");
    for (std::size_t i = 0; i < functions; ++i)
      source << "void f" << i << "(){}\n";
  }
  request.mutable_file()->set_file_path("large.cc");
  request.mutable_projection()->set_mode(ctk::analysis::v1::ValueProjection::SHALLOW);
  request.set_max_edges(200000);
  request.set_max_nodes(100000);
  EXPECT_EQ(controller.build(request, [] { return true; }).code,
            MatchCode::ResourceExhausted);
  for (const auto maximum : {std::uint64_t{functions + 1}, std::uint64_t{0}}) {
    request.set_max_nodes(maximum);
    std::size_t nodes = 0, edges = 0;
    const auto result = controller.build_stream(
        request, [] { return true; },
        [&](const auto &event, std::string &) {
          nodes += event.has_node();
          edges += event.has_edge();
          return MatchCode::Ok;
        });
    ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
    EXPECT_TRUE(result.completed.is_complete());
    EXPECT_EQ(nodes, functions + 1);
    EXPECT_EQ(edges, functions);
  }
}
TEST_F(CallGraph, LimitsCancellationAndQueueStopNeverPublishPartialGraphs) {
  request.set_max_nodes(1);
  auto nodes = controller.build(request, [] { return true; });
  EXPECT_EQ(nodes.code, MatchCode::ResourceExhausted);
  EXPECT_TRUE(nodes.response.nodes().empty());
  request.clear_max_nodes();
  request.set_max_edges(1);
  auto edges = controller.build(request, [] { return true; });
  EXPECT_EQ(edges.code, MatchCode::ResourceExhausted);
  EXPECT_TRUE(edges.response.nodes().empty());
  request.set_max_edges(0);
  EXPECT_EQ(controller.build(request, [] { return true; }).code,
            MatchCode::InvalidArgument);
  request.clear_max_edges();
  EXPECT_EQ(controller.build(request, [] { return false; }).code,
            MatchCode::Cancelled);
  CursorSettings settings;
  settings.results.max_bytes = 1;
  CallGraphController small(settings);
  EXPECT_EQ(small.build(request, [] { return true; }).code,
            MatchCode::ResourceExhausted);
  controller.stop_admission();
  EXPECT_EQ(controller.build(request, [] { return true; }).code,
            MatchCode::ResourceExhausted);
}
} // namespace
TEST_F(CallGraph, AnonymousBlocksUseTypedDeclarationsAndNativeCallExpressions) {
  std::ofstream(directory.path() / "blocks.cc")
      << "int leaf(int x){return x;} int f(){return ^(int x){return "
         "leaf(x);}(2);}";
  request.mutable_file()->set_file_path("blocks.cc");
  request.mutable_file()->add_compile_arguments("-fblocks");
  auto result = controller.build(request, [] { return true; });
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  bool block = false, call = false;
  for (const auto &node : result.response.nodes())
    if (node.has_anonymous_declaration()) {
      block = true;
      EXPECT_TRUE(node.anonymous_declaration().has_block_decl());
      EXPECT_TRUE(node.has_definition());
    }
  for (const auto &edge : result.response.edges())
    call |=
        edge.has_call() &&
        result.response.nodes(edge.callee_node()).has_anonymous_declaration();
  EXPECT_TRUE(block);
  EXPECT_TRUE(call);
}
} // namespace ctk::application
