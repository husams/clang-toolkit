#include "ctk/application/traversal_controller.hpp"
#include "ctk/clang/tooling.hpp"
#include "ctk/platform/temporary_directory.hpp"

#include <gtest/gtest.h>

#include <fstream>
#include <string>

namespace ctk::application {
namespace {
namespace pb = ctk::ast::v1;

class AvailabilityStates : public ::testing::Test {
protected:
  ctk::platform::TemporaryDirectory directory_{"ctk-availability-states"};
  ctk::analysis::v1::TraverseRequest request_;
  TraversalController controller_;

  void SetUp() override {
    std::ofstream(directory_.path() / "fixture.cc")
        << "int f(); int f() { return 1; }\n"
           "int outer() { auto nested = [] { return 2; }; return nested(); }\n"
           "template<class T> struct Box {};\n"
           "template<class T> using Alias = Box<T>;\n"
           "Alias<int> alias_value; Box<float> plain_value;\n";
    request_.mutable_file()->set_file_path("fixture.cc");
    request_.mutable_file()->set_working_directory(directory_.path().string());
    request_.mutable_file()->add_compile_arguments("-std=c++20");
  }

  ctk::analysis::v1::TraverseResponse
  traverse(ctk::analysis::v1::ValueProjection::Mode mode,
           std::uint32_t max_depth = 24) {
    auto request = request_;
    request.mutable_projection()->set_mode(mode);
    request.mutable_projection()->set_max_depth(max_depth);
    const auto result = controller_.traverse(request, [] { return true; });
    EXPECT_EQ(result.code, ctk::clang_layer::MatchCode::Ok) << result.message;
    return result.response;
  }

  static const pb::FieldAvailability *
  state(const ctk::match::v1::MatchBinding &binding, const std::string &path) {
    for (const auto &entry : binding.availability())
      if (entry.field_path() == path)
        return &entry;
    return nullptr;
  }

  static int state_count(const ctk::match::v1::MatchBinding &binding,
                         const std::string &path) {
    int count = 0;
    for (const auto &entry : binding.availability())
      count += entry.field_path() == path;
    return count;
  }

  std::vector<ctk::match::v1::MatchBinding> template_specializations() {
    auto engine = ctk::clang_layer::make_query_engine();
    const ctk::clang_layer::FileInput file{
        (directory_.path() / "fixture.cc").string(),
        {"-std=c++20"},
        directory_.path().string()};
    std::vector<ctk::match::v1::MatchBinding> result;
    const auto query = engine->match(
        file, "templateSpecializationType().bind(\"type\")",
        [] { return true; },
        [&](const ctk::clang_layer::IQueryEngine::Bindings &bindings) {
          result.push_back(bindings.at("type").value);
        });
    EXPECT_TRUE(query.ok) << query.message;
    return result;
  }
};

TEST_F(AvailabilityStates, FunctionFieldsDistinguishDefinitionAndBodyState) {
  const auto shallow = traverse(ctk::analysis::v1::ValueProjection::SHALLOW);
  int function_count = 0;
  for (const auto &record : shallow.nodes()) {
    const auto &binding = record.value();
    if (!binding.has_node() || !binding.node().has_function_decl())
      continue;
    const auto &function = binding.node().function_decl().function();
    if (function.declarator().value().named().qualified_name() != "f")
      continue;
    const auto *definition =
        state(binding, "FunctionDeclInfo.is_this_declaration_a_definition");
    ASSERT_NE(definition, nullptr);
    EXPECT_EQ(state_count(binding,
                          "FunctionDeclInfo.is_this_declaration_a_definition"),
              1);
    EXPECT_EQ(definition->state(), pb::FIELD_STATE_PRESENT);
    EXPECT_TRUE(function.has_is_this_declaration_a_definition());
    ++function_count;
    if (function.is_this_declaration_a_definition()) {
      const auto *body = state(binding, "FunctionDeclInfo.body");
      ASSERT_NE(body, nullptr);
      EXPECT_EQ(state_count(binding, "FunctionDeclInfo.body"), 1);
      EXPECT_EQ(body->state(), pb::FIELD_STATE_UNREQUESTED);
    } else {
      const auto *body = state(binding, "FunctionDeclInfo.body");
      ASSERT_NE(body, nullptr);
      EXPECT_EQ(state_count(binding, "FunctionDeclInfo.body"), 1);
      EXPECT_EQ(body->state(), pb::FIELD_STATE_SEMANTICALLY_ABSENT);
    }
  }
  EXPECT_EQ(function_count, 2);

  const auto recursive =
      traverse(ctk::analysis::v1::ValueProjection::RECURSIVE);
  bool saw_declaration = false;
  bool saw_definition = false;
  for (const auto &record : recursive.nodes()) {
    const auto &binding = record.value();
    if (!binding.has_node() || !binding.node().has_function_decl())
      continue;
    const auto &function = binding.node().function_decl().function();
    if (function.declarator().value().named().qualified_name() != "f")
      continue;
    const auto *body = state(binding, "FunctionDeclInfo.body");
    if (function.is_this_declaration_a_definition()) {
      saw_definition = true;
      ASSERT_NE(body, nullptr);
      EXPECT_EQ(state_count(binding, "FunctionDeclInfo.body"), 1);
      EXPECT_EQ(body->state(), pb::FIELD_STATE_PRESENT);
      EXPECT_TRUE(function.has_body());
    } else {
      saw_declaration = true;
      ASSERT_NE(body, nullptr);
      EXPECT_EQ(state_count(binding, "FunctionDeclInfo.body"), 1);
      EXPECT_EQ(body->state(), pb::FIELD_STATE_SEMANTICALLY_ABSENT);
      EXPECT_FALSE(function.has_body());
    }
  }
  EXPECT_TRUE(saw_declaration);
  EXPECT_TRUE(saw_definition);
}

TEST_F(AvailabilityStates, BodyBudgetFailureDoesNotReportBodyAsPresent) {
  const auto response =
      traverse(ctk::analysis::v1::ValueProjection::RECURSIVE, 1);
  bool saw_definition = false;
  bool saw_truncation = false;
  for (const auto &record : response.nodes()) {
    const auto &binding = record.value();
    if (!binding.has_node() || !binding.node().has_function_decl())
      continue;
    const auto &function = binding.node().function_decl().function();
    if (!function.is_this_declaration_a_definition())
      continue;
    saw_definition = true;
    EXPECT_FALSE(binding.is_complete());
    const auto *body = state(binding, "FunctionDeclInfo.body");
    EXPECT_TRUE(body == nullptr || body->state() != pb::FIELD_STATE_PRESENT);
    for (const auto &entry : binding.availability())
      saw_truncation |= entry.state() == pb::FIELD_STATE_TRUNCATED;
  }
  EXPECT_TRUE(saw_definition);
  EXPECT_TRUE(saw_truncation);
}

TEST_F(AvailabilityStates, NestedLambdaDoesNotConflictWithRootBodyState) {
  const auto response = traverse(ctk::analysis::v1::ValueProjection::RECURSIVE);
  bool saw_outer = false;
  for (const auto &record : response.nodes()) {
    const auto &binding = record.value();
    if (!binding.has_node() || !binding.node().has_function_decl())
      continue;
    const auto &function = binding.node().function_decl().function();
    if (function.declarator().value().named().qualified_name() != "outer")
      continue;
    saw_outer = true;
    const auto *body = state(binding, "FunctionDeclInfo.body");
    ASSERT_NE(body, nullptr);
    EXPECT_EQ(body->state(), pb::FIELD_STATE_PRESENT);
    EXPECT_EQ(state_count(binding, "FunctionDeclInfo.body"), 1);
  }
  EXPECT_TRUE(saw_outer);
}

TEST_F(AvailabilityStates, TemplateAliasPresenceAndApplicabilityAreExplicit) {
  const auto values = template_specializations();
  bool saw_alias = false;
  bool saw_non_alias = false;
  for (const auto &binding : values) {
    if (!binding.has_node() ||
        !binding.node().has_template_specialization_type())
      continue;
    const auto &type = binding.node().template_specialization_type();
    const auto *alias_flag =
        state(binding, "TemplateSpecializationType.has_alias");
    ASSERT_NE(alias_flag, nullptr);
    EXPECT_EQ(state_count(binding, "TemplateSpecializationType.has_alias"), 1);
    EXPECT_EQ(alias_flag->state(), pb::FIELD_STATE_PRESENT);
    if (type.has_has_alias() && type.has_alias() && type.has_aliased_type()) {
      saw_alias = true;
      const auto *aliased =
          state(binding, "TemplateSpecializationType.aliased_type");
      ASSERT_NE(aliased, nullptr);
      EXPECT_EQ(state_count(binding, "TemplateSpecializationType.aliased_type"),
                1);
      EXPECT_EQ(aliased->state(), pb::FIELD_STATE_PRESENT);
    } else if (type.has_has_alias() && !type.has_alias()) {
      saw_non_alias = true;
      const auto *aliased =
          state(binding, "TemplateSpecializationType.aliased_type");
      ASSERT_NE(aliased, nullptr);
      EXPECT_EQ(state_count(binding, "TemplateSpecializationType.aliased_type"),
                1);
      EXPECT_EQ(aliased->state(), pb::FIELD_STATE_INAPPLICABLE);
    }
  }
  EXPECT_TRUE(saw_alias);
  EXPECT_TRUE(saw_non_alias);
}

} // namespace
} // namespace ctk::application
