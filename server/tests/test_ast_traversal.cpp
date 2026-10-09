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
TEST_F(AstTraversal, ShallowProjectionPreservesTraversalAndBoundsOwnedPayloads) {
  auto shallow_request = request;
  shallow_request.mutable_projection()->set_mode(
      ctk::analysis::v1::ValueProjection::SHALLOW);
  auto shallow = controller.traverse(shallow_request, [] { return true; });
  ASSERT_EQ(shallow.code, MatchCode::Ok) << shallow.message;

  auto recursive_request = request;
  recursive_request.mutable_projection()->set_mode(
      ctk::analysis::v1::ValueProjection::RECURSIVE);
  auto recursive = controller.traverse(recursive_request, [] { return true; });
  ASSERT_EQ(recursive.code, MatchCode::Ok) << recursive.message;
  ASSERT_EQ(shallow.response.nodes_size(), recursive.response.nodes_size());
  EXPECT_GT(recursive.response.ByteSizeLong(),
            shallow.response.ByteSizeLong() * 2);

  bool shallow_function = false;
  bool recursive_body = false;
  for (const auto &node : shallow.response.nodes()) {
    const auto &value = node.value().node();
    if (value.has_function_decl() &&
        value.function_decl().function().declarator().value().named()
                .qualified_name() == "f") {
      shallow_function = true;
      EXPECT_FALSE(value.function_decl().function().has_body());
    }
  }
  for (const auto &node : recursive.response.nodes()) {
    const auto &value = node.value().node();
    if (value.has_function_decl() &&
        value.function_decl().function().declarator().value().named()
                .qualified_name() == "f")
      recursive_body = value.function_decl().function().has_body();
  }
  EXPECT_TRUE(shallow_function);
  EXPECT_TRUE(recursive_body);

  auto invalid = request;
  invalid.mutable_projection()->set_max_depth(0);
  EXPECT_EQ(controller.traverse(invalid, [] { return true; }).code,
            MatchCode::InvalidArgument);
  invalid.mutable_projection()->clear_max_depth();
  invalid.mutable_projection()->set_max_nodes(100001);
  EXPECT_EQ(controller.traverse(invalid, [] { return true; }).code,
            MatchCode::InvalidArgument);
}

TEST_F(AstTraversal, MainFileScopeExcludesHeaderDeclarationsAndStatements) {
  std::ofstream(directory.path() / "facts.hpp")
      << "inline int header_only() { return 9012; }\n";
  std::ofstream(directory.path() / "main_scope.cc")
      << "#include \"facts.hpp\"\n"
         "int main_only() { return header_only(); }\n";
  request.mutable_file()->set_file_path("main_scope.cc");
  request.mutable_file()->add_compile_arguments(
      "-I" + directory.path().string());

  auto all = controller.traverse(request, [] { return true; });
  ASSERT_EQ(all.code, MatchCode::Ok) << all.message;
  bool saw_header_function = false;
  bool saw_header_literal = false;
  for (const auto &record : all.response.nodes()) {
    const auto &node = record.value().node();
    if (node.has_function_decl())
      saw_header_function |=
          node.function_decl().function().declarator().value().named()
                  .qualified_name() == "header_only";
    if (node.has_integer_literal())
      saw_header_literal |=
          node.integer_literal().value().unsigned_decimal() == "9012";
  }
  EXPECT_TRUE(saw_header_function);
  EXPECT_TRUE(saw_header_literal);

  request.set_main_file_only(true);
  auto main_only = controller.traverse(request, [] { return true; });
  ASSERT_EQ(main_only.code, MatchCode::Ok) << main_only.message;
  EXPECT_FALSE(main_only.response.depth_limited());
  for (const auto &record : main_only.response.nodes()) {
    const auto &node = record.value().node();
    if (node.has_function_decl())
      EXPECT_NE(node.function_decl().function().declarator().value().named()
                    .qualified_name(),
                "header_only");
    if (node.has_integer_literal())
      EXPECT_NE(node.integer_literal().value().unsigned_decimal(), "9012");
  }
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
