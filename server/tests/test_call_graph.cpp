#include "ctk/application/call_graph_controller.hpp"
#include "ctk/platform/temporary_directory.hpp"
#include <fstream>
#include <gtest/gtest.h>
#include <map>
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
