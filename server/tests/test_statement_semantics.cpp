#include "ctk/clang/tooling.hpp"
#include "ctk/platform/temporary_directory.hpp"
#include <fstream>
#include <gtest/gtest.h>
#include <memory>
#include <vector>

namespace ctk::clang_layer {
namespace {
struct Fixture {
  ctk::platform::TemporaryDirectory directory{"ctk-statement-semantics"};
  FileInput file;
  Fixture(const std::string &source) {
    auto path = directory.path() / "fixture.cc";
    std::ofstream(path) << source;
    file = {path.string(), {"-std=c++23"}, directory.path().string()};
  }
};
std::vector<ctk::match::v1::MatchBinding> query(const FileInput &file,
                                                const std::string &matcher) {
  std::vector<ctk::match::v1::MatchBinding> result;
  auto engine = make_query_engine();
  auto status = engine->match(
      file, matcher, [] { return true; },
      [&](const IQueryEngine::Bindings &row) {
        result.push_back(row.at("node").value);
      });
  EXPECT_TRUE(status.ok) << status.message;
  return result;
}
bool has_unrequested(const ctk::match::v1::MatchBinding &binding,
                     const std::string &suffix) {
  for (const auto &entry : binding.availability())
    if (entry.state() == ctk::ast::v1::FIELD_STATE_UNREQUESTED &&
        entry.field_path().ends_with(suffix))
      return true;
  return false;
}
TEST(StatementSemantics, ConditionsPreserveFlagsAndReportUnrequestedBranches) {
  Fixture f("int f(int x) { if (int y = x; y) ++x; for (int i=0;i<3;++i) x+=i; "
            "while(false) ; return x; }");
  auto values = query(f.file, "ifStmt().bind(\"node\")");
  ASSERT_EQ(values.size(), 1U);
  const auto &branch = values[0].node().if_stmt();
  EXPECT_FALSE(branch.has_init_statement());
  EXPECT_FALSE(branch.has_condition_variable());
  EXPECT_TRUE(has_unrequested(values[0], "init_statement"));
  EXPECT_FALSE(branch.has_else_statement());
  EXPECT_TRUE(branch.has_is_constexpr());
  EXPECT_FALSE(branch.is_constexpr());
  EXPECT_TRUE(values[0].is_complete());
  auto loop = query(f.file, "forStmt().bind(\"node\")");
  ASSERT_EQ(loop.size(), 1U);
  EXPECT_FALSE(loop[0].node().for_stmt().has_increment());
  EXPECT_FALSE(loop[0].node().for_stmt().has_body());
  EXPECT_TRUE(loop[0].is_complete());
  EXPECT_TRUE(has_unrequested(loop[0], "increment"));
  EXPECT_TRUE(has_unrequested(loop[0], "body"));
  auto whiles = query(f.file, "whileStmt().bind(\"node\")");
  ASSERT_EQ(whiles.size(), 1U);
  EXPECT_FALSE(whiles[0].node().while_stmt().has_is_condition_false());
  EXPECT_TRUE(has_unrequested(whiles[0], "WhileStmt.is_condition_false"));
  EXPECT_FALSE(whiles[0].node().while_stmt().has_body());
  EXPECT_TRUE(whiles[0].is_complete());
  EXPECT_TRUE(has_unrequested(whiles[0], "body"));
}
TEST(StatementSemantics, SwitchCasesTryHandlersAndFiniteGotoSymbols) {
  Fixture f("int f(int x) { switch(x) { case 1: break; default: x=0; } try { "
            "if(x) goto end; } catch(int v) { x=v; } catch(...) { x=-1; } end: "
            "return x; }");
  auto values = query(f.file, "switchStmt().bind(\"node\")");
  ASSERT_EQ(values.size(), 1U);
  EXPECT_FALSE(values[0].node().switch_stmt().has_default_case());
  EXPECT_FALSE(values[0].node().switch_stmt().has_condition());
  EXPECT_TRUE(values[0].is_complete());
  EXPECT_TRUE(has_unrequested(values[0], "default_case"));
  auto tries = query(f.file, "cxxTryStmt().bind(\"node\")");
  ASSERT_EQ(tries.size(), 1U);
  EXPECT_EQ(tries[0].node().cxx_try_stmt().handlers_size(), 0);
  EXPECT_FALSE(tries[0].node().cxx_try_stmt().has_try_block());
  EXPECT_TRUE(tries[0].is_complete());
  EXPECT_TRUE(has_unrequested(tries[0], "handlers"));
  auto gotos = query(f.file, "gotoStmt().bind(\"node\")");
  ASSERT_EQ(gotos.size(), 1U);
  EXPECT_EQ(gotos[0].node().goto_stmt().target_label().name(), "end");
  EXPECT_EQ(gotos[0].node().goto_stmt().target_label().kind(),
            ctk::ast::v1::SYMBOL_KIND_LABEL);
}
TEST(StatementSemantics, ProtobufValuesSurviveNativeOwnersAndRoundTrip) {
  Fixture f("unsigned value = 0xFEDCBA98u; void f() { if (false) ; }");
  auto values = query(f.file, "integerLiteral().bind(\"node\")");
  ASSERT_EQ(values.size(), 1U);
  ctk::match::v1::MatchBinding copied;
  ASSERT_TRUE(copied.ParseFromString(values[0].SerializeAsString()));
  EXPECT_EQ(copied.node().integer_literal().value().unsigned_decimal(),
            "4275878552");
  EXPECT_TRUE(copied.is_complete());
  EXPECT_TRUE(has_unrequested(copied, "QualType.type"));
  for (const auto &entry : copied.availability()) {
    EXPECT_NE(entry.state(), ctk::ast::v1::FIELD_STATE_UNAVAILABLE);
    EXPECT_NE(entry.state(), ctk::ast::v1::FIELD_STATE_TRUNCATED);
  }
  EXPECT_EQ(copied.supported_scopes_size(), 2);
}
TEST(StatementSemantics,
     PublicExpressionProjectionDoesNotExpandOrTruncateNestedOperators) {
  std::string expression = "1";
  for (unsigned i = 0; i < 60; ++i)
    expression += "+1";
  Fixture f("int f() { return " + expression + "; }");
  auto values = query(f.file, "binaryOperator().bind(\"node\")");
  ASSERT_EQ(values.size(), 60U);
  for (const auto &binding : values) {
    ctk::match::v1::MatchBinding copy;
    EXPECT_TRUE(copy.ParseFromString(binding.SerializeAsString()));
    EXPECT_TRUE(binding.is_complete());
    EXPECT_FALSE(binding.node().binary_operator().has_left());
    EXPECT_FALSE(binding.node().binary_operator().has_right());
    for (const auto &entry : binding.availability())
      EXPECT_NE(entry.state(), ctk::ast::v1::FIELD_STATE_TRUNCATED);
  }
}
TEST(StatementSemantics, BindingRowsPreserveMultiplicityAndAutomaticRoot) {
  Fixture f("int f() { return 1+2; }");
  auto engine = make_query_engine();
  unsigned rows = 0;
  auto result = engine->match(
      f.file, "integerLiteral()", [] { return true; },
      [&](const IQueryEngine::Bindings &row) {
        ++rows;
        ASSERT_EQ(row.size(), 1U);
        EXPECT_TRUE(row.at("root").value.node().has_integer_literal());
      });
  EXPECT_TRUE(result.ok) << result.message;
  EXPECT_EQ(rows, 2U);
  rows = 0;
  result = engine->match(
      f.file,
      "functionDecl(hasName(\"f\"), "
      "forEachDescendant(integerLiteral().bind(\"literal\"))).bind(\"node\")",
      [] { return true; },
      [&](const IQueryEngine::Bindings &row) {
        ++rows;
        EXPECT_TRUE(row.at("node").value.node().has_function_decl());
        EXPECT_TRUE(row.at("root").value.node().has_function_decl());
        EXPECT_TRUE(row.at("literal").value.node().has_integer_literal());
      });
  EXPECT_TRUE(result.ok) << result.message;
  EXPECT_EQ(rows, 2U);
}
TEST(StatementSemantics, CachedConstantValuesKeepScalars) {
  Fixture f("enum E { negative = -7 };");
  const auto query_constants = [&](const std::shared_ptr<IQueryEngine> &engine,
                                   std::vector<ctk::match::v1::MatchBinding> &rows) {
    const auto status = engine->match(
        f.file, "constantExpr().bind(\"node\")", [] { return true; },
        [&](const IQueryEngine::Bindings &bindings) {
          rows.push_back(bindings.at("node").value);
        });
    EXPECT_TRUE(status.ok) << status.message;
    return status;
  };
  std::vector<ctk::match::v1::MatchBinding> seeded;
  const auto first = query_constants(make_query_engine(), seeded);
  ASSERT_TRUE(first.ok) << first.message;

  std::vector<ctk::match::v1::MatchBinding> loaded;
  const auto reloaded = query_constants(make_query_engine(), loaded);
  ASSERT_TRUE(reloaded.ok) << reloaded.message;
  EXPECT_TRUE(reloaded.storage_hit) << reloaded.storage_message;

  bool saw_scalar = false;
  for (const auto &binding : loaded) {
    const auto &constant = binding.node().constant_expr();
    if (constant.value().has_integer() &&
        constant.value().integer().decimal_value() == "-7") {
      saw_scalar = true;
      EXPECT_TRUE(binding.is_complete());
      EXPECT_EQ(constant.value().integer().decimal_value(), "-7");
    }
  }
  EXPECT_TRUE(saw_scalar);
}

} // namespace
} // namespace ctk::clang_layer
