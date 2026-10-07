#include "ctk/application/traversal_controller.hpp"
#include "ctk/platform/temporary_directory.hpp"
#include <fstream>
#include <gtest/gtest.h>

namespace ctk::application {
namespace {
using ctk::clang_layer::MatchCode;
class AstTraversal : public ::testing::Test {
protected:
  ctk::platform::TemporaryDirectory directory{"ctk-traversal"};
  TraversalController controller;
  ctk::analysis::v1::TraverseRequest request;
  void SetUp() override {
    std::ofstream(directory.path() / "fixture.cc")
        << "template<class T> T id(T x){return x;}\n"
           "int f(){int n=7; return id(n);}";
    request.mutable_file()->set_file_path("fixture.cc");
    request.mutable_file()->set_working_directory(directory.path().string());
    request.mutable_file()->add_compile_arguments("-std=c++20");
  }
};
TEST_F(AstTraversal,
       NativePreorderContainsOwnedSemanticNodesAndDeclarationStatements) {
  auto result = controller.traverse(request, [] { return true; });
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  ASSERT_GT(result.response.nodes_size(), 5);
  EXPECT_FALSE(result.response.nodes(0).has_parent_index());
  EXPECT_TRUE(
      result.response.nodes(0).value().node().has_translation_unit_decl());
  bool saw_literal = false, saw_call = false, saw_decl_stmt = false;
  for (int i = 1; i < result.response.nodes_size(); ++i) {
    const auto &record = result.response.nodes(i);
    ASSERT_TRUE(record.has_parent_index());
    ASSERT_LT(record.parent_index(), static_cast<std::uint64_t>(i));
    EXPECT_EQ(record.depth(),
              result.response.nodes(record.parent_index()).depth() + 1);
    const auto &value = record.value().node();
    saw_call |= value.has_call_expr();
    saw_decl_stmt |= value.has_decl_stmt();
    if (value.has_integer_literal()) {
      saw_literal = true;
      EXPECT_EQ(value.integer_literal().value().unsigned_decimal(), "7");
    }
  }
  EXPECT_TRUE(saw_literal);
  EXPECT_TRUE(saw_call);
  EXPECT_TRUE(saw_decl_stmt);
  EXPECT_FALSE(result.response.depth_limited());
  const auto copied = result.response.SerializeAsString();
  std::filesystem::remove(directory.path() / "fixture.cc");
  EXPECT_EQ(result.response.SerializeAsString(), copied);
}
TEST_F(AstTraversal,
       ExplicitDepthZeroPrunesDescendantsAndNodeLimitReturnsNoPartialResponse) {
  request.set_max_depth(0);
  auto root = controller.traverse(request, [] { return true; });
  ASSERT_EQ(root.code, MatchCode::Ok) << root.message;
  EXPECT_EQ(root.response.nodes_size(), 1);
  EXPECT_TRUE(root.response.depth_limited());
  request.clear_max_depth();
  request.set_max_nodes(1);
  auto failed = controller.traverse(request, [] { return true; });
  EXPECT_EQ(failed.code, MatchCode::ResourceExhausted);
  EXPECT_EQ(failed.response.nodes_size(), 0);
  request.set_max_nodes(0);
  EXPECT_EQ(controller.traverse(request, [] { return true; }).code,
            MatchCode::InvalidArgument);
}
TEST_F(AstTraversal,
       NativeTemplateAndImplicitOptionsChangeTheVisitedOccurrences) {
  auto plain = controller.traverse(request, [] { return true; });
  request.set_visit_template_instantiations(true);
  auto instantiated = controller.traverse(request, [] { return true; });
  request.set_visit_implicit_code(true);
  auto implicit = controller.traverse(request, [] { return true; });
  ASSERT_EQ(plain.code, MatchCode::Ok);
  ASSERT_EQ(instantiated.code, MatchCode::Ok);
  ASSERT_EQ(implicit.code, MatchCode::Ok);
  EXPECT_GT(instantiated.response.nodes_size(), plain.response.nodes_size());
  EXPECT_GT(implicit.response.nodes_size(), instantiated.response.nodes_size());
}
TEST_F(AstTraversal,
       CancellationByteLimitsAndInvalidCompilerFlagsDoNotReturnPartialTrees) {
  auto cancelled = controller.traverse(request, [] { return false; });
  EXPECT_EQ(cancelled.code, MatchCode::Cancelled);
  EXPECT_TRUE(cancelled.response.nodes().empty());
  CursorSettings settings;
  settings.results.max_bytes = 1;
  TraversalController limited(settings);
  auto bytes = limited.traverse(request, [] { return true; });
  EXPECT_EQ(bytes.code, MatchCode::ResourceExhausted);
  EXPECT_TRUE(bytes.response.nodes().empty());
  request.mutable_file()->add_compile_arguments("-o");
  EXPECT_EQ(controller.traverse(request, [] { return true; }).code,
            MatchCode::InvalidArgument);
  request.mutable_file()->clear_compile_arguments();
  controller.stop_admission();
  EXPECT_EQ(controller.traverse(request, [] { return true; }).code,
            MatchCode::ResourceExhausted);
}
} // namespace
} // namespace ctk::application
