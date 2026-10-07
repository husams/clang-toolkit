#include "ctk/application/cfg_controller.hpp"
#include "ctk/platform/temporary_directory.hpp"
#include <fstream>
#include <gtest/gtest.h>
#include <set>
namespace ctk::application {
namespace {
using ctk::clang_layer::MatchCode;
using Element = ctk::analysis::v1::CfgElement;
class ControlFlow : public ::testing::Test {
protected:
  ctk::platform::TemporaryDirectory directory{"ctk-cfg"};
  CfgController controller;
  ctk::analysis::v1::CfgRequest request;
  void SetUp() override {
    std::ofstream(directory.path() / "fixture.cc") << R"cpp(
struct Base { Base(); virtual ~Base(); };
struct A : virtual Base { A(); A(const A&); ~A(); int x=7; };
struct Derived : A { A member; Derived(): member() {} ~Derived() {} };
A make(); void consume(A); void clean(int*);
namespace ns {
int f(int x) { int y=7; if (false) y=9; if (x) return y; return 2; }
int f(double x) { return int(x); }
}
void rich() { A a; consume(make()); auto *p=new A; delete p; for(int n=0; n<2; ++n) { A b; } int q __attribute__((cleanup(clean)))=0; }
A returned(){return A();}
template<class T> T dependent(T x){return x;}
[[noreturn]] void die(); void stop(){die();}
)cpp";
    request.mutable_file()->set_file_path("fixture.cc");
    request.mutable_file()->set_working_directory(directory.path().string());
    request.mutable_file()->add_compile_arguments("-std=c++20");
    request.set_function("ns::f");
  }
};
TEST_F(ControlFlow, TypedOverloadsPreservePrunedEdgeSlotsAndOwnedBlocks) {
  auto result = controller.build(request, [] { return true; });
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  ASSERT_EQ(result.response.graphs_size(), 2);
  bool pruned = false, literal = false;
  for (const auto &graph : result.response.graphs()) {
    EXPECT_EQ(graph.function().qualified_name(), "ns::f");
    std::set<std::uint64_t> indices;
    for (const auto &block : graph.blocks()) {
      indices.insert(block.block_index());
      for (const auto &edge : block.successors())
        pruned |= !edge.has_reachable_block() &&
                  edge.has_possibly_unreachable_block();
      for (const auto &element : block.elements()) {
        ASSERT_NE(element.kind(), Element::KIND_UNSPECIFIED);
        if (element.has_statement())
          literal |= element.statement()
                         .statement()
                         .expression()
                         .has_integer_literal();
      }
    }
    EXPECT_TRUE(indices.contains(graph.entry_block()));
    EXPECT_TRUE(indices.contains(graph.exit_block()));
    for (const auto &block : graph.blocks())
      for (const auto &edge : block.successors()) {
        if (edge.has_reachable_block())
          EXPECT_TRUE(indices.contains(edge.reachable_block()));
        if (edge.has_possibly_unreachable_block())
          EXPECT_TRUE(indices.contains(edge.possibly_unreachable_block()));
      }
  }
  EXPECT_TRUE(pruned);
  EXPECT_TRUE(literal);
  request.mutable_options()->set_prune_trivially_false_edges(false);
  auto unpruned = controller.build(request, [] { return true; });
  ASSERT_EQ(unpruned.code, MatchCode::Ok);
  for (const auto &graph : unpruned.response.graphs())
    for (const auto &block : graph.blocks())
      for (const auto &edge : block.successors())
        EXPECT_FALSE(edge.has_possibly_unreachable_block());
  const auto owned = result.response.SerializeAsString();
  std::filesystem::remove(directory.path() / "fixture.cc");
  EXPECT_EQ(result.response.SerializeAsString(), owned);
}
TEST_F(ControlFlow, RichOptionsExposeConstructionContextsAndLifetimeEvents) {
  request.set_function("rich");
  auto *options = request.mutable_options();
  options->set_add_implicit_dtors(true);
  options->set_add_temporary_dtors(true);
  options->set_add_lifetime(true);
  options->set_add_scopes(true);
  options->set_add_loop_exit(true);
  options->set_add_cxx_new_allocator(true);
  options->set_add_rich_cxx_constructors(true);
  options->set_mark_elided_cxx_constructors(true);
  options->set_always_add_statements(true);
  auto result = controller.build(request, [] { return true; });
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  std::set<int> kinds;
  bool construction = false, named_dtor = false;
  for (const auto &block : result.response.graphs(0).blocks())
    for (const auto &element : block.elements()) {
      kinds.insert(element.kind());
      if (element.has_statement() &&
          element.statement().has_construction_context()) {
        construction = true;
        EXPECT_NE(element.statement().construction_context().kind(),
                  ctk::analysis::v1::CfgConstructionContext::KIND_UNSPECIFIED);
      }
      if (element.has_destructor() && element.destructor().has_destructor())
        named_dtor |=
            !element.destructor().destructor().qualified_name().empty();
    }
  for (int kind :
       {Element::CONSTRUCTOR, Element::NEW_ALLOCATOR,
        Element::AUTOMATIC_OBJECT_DTOR, Element::DELETE_DTOR,
        Element::TEMPORARY_DTOR, Element::SCOPE_BEGIN, Element::SCOPE_END,
        Element::LIFETIME_ENDS, Element::LOOP_EXIT, Element::CLEANUP_FUNCTION})
    EXPECT_TRUE(kinds.contains(kind)) << kind;
  EXPECT_TRUE(construction);
  EXPECT_TRUE(named_dtor);
  request.set_function("Derived::Derived");
  options->set_add_initializers(true);
  options->set_add_virtual_base_branches(true);
  auto initializers = controller.build(request, [] { return true; });
  ASSERT_EQ(initializers.code, MatchCode::Ok) << initializers.message;
  bool initializer = false;
  for (const auto &block : initializers.response.graphs(0).blocks())
    for (const auto &element : block.elements())
      initializer |= element.has_initializer();
  EXPECT_TRUE(initializer);
}
TEST_F(ControlFlow, MissingDependentAndNoReturnFunctionsHaveDistinctBehavior) {
  request.set_function("missing");
  EXPECT_EQ(controller.build(request, [] { return true; }).code,
            MatchCode::NotFound);
  request.set_function("dependent");
  EXPECT_EQ(controller.build(request, [] { return true; }).code,
            MatchCode::FailedPrecondition);
  request.set_function("stop");
  auto result = controller.build(request, [] { return true; });
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  bool no_return = false;
  for (const auto &block : result.response.graphs(0).blocks())
    no_return |= block.has_no_return_element();
  EXPECT_TRUE(no_return);
}
TEST_F(ControlFlow, LimitsCancellationAndStopNeverPublishPartialGraphs) {
  request.set_max_functions(1);
  auto functions = controller.build(request, [] { return true; });
  EXPECT_EQ(functions.code, MatchCode::ResourceExhausted);
  EXPECT_TRUE(functions.response.graphs().empty());
  request.clear_max_functions();
  request.set_max_blocks(1);
  EXPECT_EQ(controller.build(request, [] { return true; }).code,
            MatchCode::ResourceExhausted);
  request.clear_max_blocks();
  request.set_max_elements(1);
  EXPECT_EQ(controller.build(request, [] { return true; }).code,
            MatchCode::ResourceExhausted);
  request.set_max_elements(0);
  EXPECT_EQ(controller.build(request, [] { return true; }).code,
            MatchCode::InvalidArgument);
  request.clear_max_elements();
  auto cancelled = controller.build(request, [] { return false; });
  EXPECT_EQ(cancelled.code, MatchCode::Cancelled);
  EXPECT_TRUE(cancelled.response.graphs().empty());
  CursorSettings settings;
  settings.results.max_bytes = 1;
  CfgController small(settings);
  EXPECT_EQ(small.build(request, [] { return true; }).code,
            MatchCode::ResourceExhausted);
  controller.stop_admission();
  EXPECT_EQ(controller.build(request, [] { return true; }).code,
            MatchCode::ResourceExhausted);
}
} // namespace
TEST_F(ControlFlow, NativeFixturesExerciseAllElementAndConstructionKinds) {
  std::ofstream(directory.path() / "contexts.cc") << R"cpp(
struct A { A(); A(const A&); ~A(); };
struct Plain { Plain(); Plain(const Plain&); };
A make(){return A();} Plain plain(){return Plain();}
void consume(A); void clean(int*);
struct Base { A value; Base():value() {} virtual ~Base(){} };
struct Derived : virtual Base { A member; Derived():member(make()){} ~Derived(){} };
void contexts(){ A a; A b=make(); A c=A(); consume(A()); auto *p=new A(); delete p; const A& r=A(); auto l=[a]{}; Plain t=plain(); for(int i=0;i<2;++i){A x;} int q __attribute__((cleanup(clean)))=0; }
)cpp";
  request.mutable_file()->set_file_path("contexts.cc");
  auto *options = request.mutable_options();
  options->set_add_initializers(true);
  options->set_add_implicit_dtors(true);
  options->set_add_temporary_dtors(true);
  options->set_add_lifetime(true);
  options->set_add_scopes(true);
  options->set_add_loop_exit(true);
  options->set_add_cxx_new_allocator(true);
  options->set_add_rich_cxx_constructors(true);
  options->set_mark_elided_cxx_constructors(true);
  options->set_add_virtual_base_branches(true);
  options->set_always_add_statements(true);
  std::set<int> kinds, constructions;
  const auto collect =
      [&](const auto &self,
          const ctk::analysis::v1::CfgConstructionContext &value) -> void {
    constructions.insert(value.kind());
    if (value.has_context_after_elision())
      self(self, value.context_after_elision());
  };
  for (const auto *standard : {"-std=c++14", "-std=c++20"}) {
    request.mutable_file()->clear_compile_arguments();
    request.mutable_file()->add_compile_arguments(standard);
    for (const auto *function :
         {"make", "plain", "Base::Base", "Base::~Base", "Derived::Derived",
          "Derived::~Derived", "contexts"}) {
      request.set_function(function);
      auto result = controller.build(request, [] { return true; });
      ASSERT_EQ(result.code, MatchCode::Ok)
          << function << " " << standard << " " << result.message;
      for (const auto &graph : result.response.graphs())
        for (const auto &block : graph.blocks())
          for (const auto &element : block.elements()) {
            kinds.insert(element.kind());
            if (element.has_statement() &&
                element.statement().has_construction_context())
              collect(collect, element.statement().construction_context());
          }
    }
  }
  for (int kind = 1; kind <= 15; ++kind)
    EXPECT_TRUE(kinds.contains(kind)) << "element " << kind;
  for (int kind = 1; kind <= 11; ++kind)
    EXPECT_TRUE(constructions.contains(kind)) << "construction " << kind;
}
TEST_F(ControlFlow, VersionSpecificBuildOptionIsExplicitlySupportedOrRejected) {
  request.mutable_options()->set_assume_reachable_default_in_switch_statements(
      true);
  auto result = controller.build(request, [] { return true; });
#if CTK_TEST_CLANG_VERSION_MAJOR >= 22
  EXPECT_EQ(result.code, MatchCode::Ok) << result.message;
#else
  EXPECT_EQ(result.code, MatchCode::FailedPrecondition);
  EXPECT_TRUE(result.response.graphs().empty());
#endif
}
} // namespace ctk::application
