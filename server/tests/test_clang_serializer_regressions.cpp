#include "ctk/clang/tooling.hpp"
#include "ctk/platform/temporary_directory.hpp"

#include "ast/v1/node.pb.h"
#include "ast/v1/record_type.pb.h"

#include <gtest/gtest.h>

#include <filesystem>
#include <fstream>
#include <memory>
#include <string>
#include <vector>

namespace ctk::clang_layer {
namespace {

bool has_unrequested(const ctk::match::v1::MatchBinding &binding,
                     const std::string &field_suffix) {
  for (const auto &entry : binding.availability()) {
    if (entry.state() == ctk::ast::v1::FIELD_STATE_UNREQUESTED &&
        entry.field_path().size() >= field_suffix.size() &&
        entry.field_path().compare(entry.field_path().size() - field_suffix.size(),
                                   field_suffix.size(), field_suffix) == 0)
      return true;
  }
  return false;
}

std::vector<ctk::match::v1::MatchBinding>
match_one_file(const std::shared_ptr<IQueryEngine> &engine,
               const std::filesystem::path &path, const std::string &source,
               const std::string &query, const std::string &binding_name) {
  {
    std::ofstream output(path);
    output << source;
  }
  std::vector<ctk::match::v1::MatchBinding> rows;
  const FileInput file{path.string(), {"-std=c++20"},
                       std::filesystem::current_path().string()};
  const auto result = engine->match(
      file, query, [] { return true; },
      [&](const IQueryEngine::Bindings &bindings) {
        rows.push_back(bindings.at(binding_name).value);
      });
  EXPECT_TRUE(result.ok) << result.message;
  return rows;
}

TEST(ClangSerializerRegressions,
     PreservesAliasObjectTypeAndSerializesDirectRecordType) {
  ctk::platform::TemporaryDirectory directory("ctk-object-type-regression");
  const auto path = directory.path() / "fixture.cc";
  {
    std::ofstream output(path);
    output << "struct Box { int get() { return 7; } };\n"
              "using Alias = Box;\n"
              "int through_alias(Alias& box) { return box.get(); }\n"
              "int direct(Box& box) { return box.get(); }\n";
  }

  auto engine = make_query_engine();
  const FileInput file{
      path.string(), {"-std=c++20"}, std::filesystem::current_path().string()};
  const auto check_function_type = [&](const std::string &function_name,
                                       bool alias_object) {
    std::size_t matches = 0;
    bool saw_expected_type = false;
    const auto query = "callExpr(hasAncestor(functionDecl(hasName(\"" +
                       function_name + "\")))).bind(\"call\")";
    const auto result = engine->match(
        file, query, [] { return true; },
        [&](const IQueryEngine::Bindings &bindings) {
          ++matches;
          const auto &match = bindings.at("call").value;
          const auto &call = match.node();
          ASSERT_TRUE(call.has_cxx_member_call_expr());
          const auto &object_type = call.cxx_member_call_expr().object_type().type();
          EXPECT_EQ(call.cxx_member_call_expr().object_type().description().spelling(),
                    alias_object ? "Alias" : "Box");
          EXPECT_EQ(object_type.payload_case(),
                    ctk::ast::v1::TypeValue::PAYLOAD_NOT_SET);
          EXPECT_TRUE(match.is_complete());
          saw_expected_type = true;
        });

    EXPECT_TRUE(result.ok) << result.message;
    EXPECT_EQ(matches, 1U);
    EXPECT_TRUE(saw_expected_type);
  };

  check_function_type("through_alias", true);
  check_function_type("direct", false);
}

TEST(ClangSerializerRegressions,
     PublicMatchProjectsImmediateFieldsAndReportsUnrequestedChildren) {
  ctk::platform::TemporaryDirectory directory("ctk-shallow-projection");
  const auto path = directory.path() / "fixture.cc";
  auto engine = make_query_engine();
  const std::string source =
      "struct Record { int member; };\n"
      "int *pointer;\n"
      "int global = 7;\n"
      "int calculate(int value) { int local = value; return local + 1; }\n";

  auto rows = match_one_file(
      engine, path, source,
      "functionDecl(hasName(\"calculate\")).bind(\"node\")", "node");
  ASSERT_EQ(rows.size(), 1U);
  const auto &function = rows.front().node().function_decl().function();
  EXPECT_FALSE(function.is_constexpr());
  EXPECT_EQ(function.return_type().description().spelling(), "int");
  EXPECT_EQ(function.parameters_size(), 0);
  EXPECT_FALSE(function.has_body());
  EXPECT_TRUE(rows.front().is_complete());
  EXPECT_TRUE(has_unrequested(rows.front(), "parameters"));
  EXPECT_TRUE(has_unrequested(rows.front(), "body"));

  rows = match_one_file(engine, path, source,
                        "varDecl(hasName(\"global\")).bind(\"node\")",
                        "node");
  ASSERT_EQ(rows.size(), 1U);
  const auto &variable = rows.front().node().var_decl();
  EXPECT_EQ(variable.variable().declarator().value().type().description().spelling(),
            "int");
  EXPECT_FALSE(variable.variable().has_initializer());
  EXPECT_FALSE(variable.has_initializer_from_any_declaration());
  EXPECT_EQ(variable.initialization_style(),
            ctk::ast::v1::DECL_VARIABLE_INITIALIZATION_STYLE_C);
  EXPECT_TRUE(rows.front().is_complete());
  EXPECT_TRUE(has_unrequested(rows.front(), "initializer"));

  rows = match_one_file(
      engine, path, source,
      "binaryOperator(hasOperatorName(\"+\")).bind(\"node\")", "node");
  ASSERT_EQ(rows.size(), 1U);
  const auto &binary = rows.front().node().binary_operator();
  EXPECT_EQ(binary.opcode(), ctk::ast::v1::BINARY_OPCODE_ADD);
  EXPECT_FALSE(binary.has_left());
  EXPECT_FALSE(binary.has_right());
  EXPECT_EQ(binary.info().type().description().spelling(), "int");
  EXPECT_TRUE(rows.front().is_complete());
  EXPECT_TRUE(has_unrequested(rows.front(), "left"));
  EXPECT_TRUE(has_unrequested(rows.front(), "right"));

  rows = match_one_file(engine, path, source,
                        "compoundStmt().bind(\"node\")", "node");
  ASSERT_EQ(rows.size(), 1U);
  EXPECT_EQ(rows.front().node().compound_stmt().body_size(), 0);
  EXPECT_FALSE(rows.front().node().compound_stmt().has_is_statement_expression());
  EXPECT_TRUE(has_unrequested(rows.front(), "CompoundStmt.is_statement_expression"));
  EXPECT_TRUE(rows.front().is_complete());
  EXPECT_TRUE(has_unrequested(rows.front(), "CompoundStmt.body"));

  rows = match_one_file(
      engine, path, source,
      "cxxRecordDecl(hasName(\"Record\"), isDefinition()).bind(\"node\")", "node");
  ASSERT_EQ(rows.size(), 1U);
  EXPECT_EQ(rows.front().node().cxx_record_decl().record().tag().tag_kind(),
            ctk::ast::v1::TAG_KIND_STRUCT);
  EXPECT_EQ(rows.front().node().cxx_record_decl().record().members_size(), 0);
  EXPECT_TRUE(rows.front().is_complete());
  EXPECT_TRUE(has_unrequested(rows.front(), "members"));

  rows = match_one_file(engine, path, source,
                        "pointerType(pointee(asString(\"int\"))).bind(\"node\")", "node");
  ASSERT_FALSE(rows.empty());
  const auto &pointee = rows.front().node().pointer_type().pointee_type();
  EXPECT_EQ(pointee.description().spelling(), "int");
  EXPECT_EQ(pointee.type().payload_case(),
            ctk::ast::v1::TypeValue::PAYLOAD_NOT_SET);
  EXPECT_TRUE(has_unrequested(rows.front(), "QualType.type"));
  EXPECT_TRUE(rows.front().node().pointer_type().info().has_spelling());
  EXPECT_TRUE(rows.front().is_complete());
}

TEST(ClangSerializerRegressions,
     PublicFunctionResultSizeDoesNotGrowWithBodySize) {
  ctk::platform::TemporaryDirectory directory("ctk-shallow-size");
  const auto path = directory.path() / "fixture.cc";
  auto engine = make_query_engine();
  const auto small = match_one_file(
      engine, path, "int work() { return 1; }",
      "functionDecl(hasName(\"work\")).bind(\"node\")", "node");
  ASSERT_EQ(small.size(), 1U);

  std::string large_source = "int work() {\n";
  for (int i = 0; i < 500; ++i)
    large_source += "int local" + std::to_string(i) + " = " +
                    std::to_string(i) + ";\n";
  large_source += "return 1; }\n";
  const auto large = match_one_file(
      engine, path, large_source,
      "functionDecl(hasName(\"work\")).bind(\"node\")", "node");
  ASSERT_EQ(large.size(), 1U);
  EXPECT_EQ(small.front().ByteSizeLong(), large.front().ByteSizeLong());
  EXPECT_TRUE(large.front().is_complete());
  EXPECT_TRUE(has_unrequested(large.front(), "body"));
}

} // namespace
} // namespace ctk::clang_layer
