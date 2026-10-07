#include "ctk/clang/tooling.hpp"
#include "ctk/platform/temporary_directory.hpp"
#include <fstream>
#include <gtest/gtest.h>
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
TEST(StatementSemantics, ConditionsPreserveAbsentBranchesAndOwnedDeclarations) {
  Fixture f("int f(int x) { if (int y = x; y) ++x; for (int i=0;i<3;++i) x+=i; "
            "while(false) ; return x; }");
  auto values = query(f.file, "ifStmt().bind(\"node\")");
  ASSERT_EQ(values.size(), 1U);
  const auto &branch = values[0].node().if_stmt();
  ASSERT_TRUE(branch.has_init_statement());
  ASSERT_TRUE(branch.init_statement().has_decl_stmt());
  ASSERT_EQ(branch.init_statement().decl_stmt().declarations_size(), 1);
  const auto &decl =
      branch.init_statement().decl_stmt().declarations(0).var_decl();
  EXPECT_EQ(decl.variable().declarator().value().named().qualified_name(), "y");
  EXPECT_TRUE(decl.variable().has_initializer());
  EXPECT_FALSE(branch.has_else_statement());
  EXPECT_FALSE(branch.has_condition_variable());
  EXPECT_TRUE(branch.has_is_constexpr());
  EXPECT_FALSE(branch.is_constexpr());
  EXPECT_TRUE(values[0].is_complete());
  auto loop = query(f.file, "forStmt().bind(\"node\")");
  ASSERT_EQ(loop.size(), 1U);
  EXPECT_TRUE(loop[0].node().for_stmt().has_increment());
  EXPECT_EQ(loop[0]
                .node()
                .for_stmt()
                .body()
                .expression()
                .compound_assign_operator()
                .opcode(),
            ctk::ast::v1::BINARY_OPCODE_ADD_ASSIGN);
  auto whiles = query(f.file, "whileStmt().bind(\"node\")");
  ASSERT_EQ(whiles.size(), 1U);
  EXPECT_TRUE(whiles[0].node().while_stmt().is_condition_false());
  EXPECT_TRUE(whiles[0].node().while_stmt().body().has_null_stmt());
  EXPECT_TRUE(whiles[0].is_complete());
}
TEST(StatementSemantics, SwitchCasesTryHandlersAndFiniteGotoSymbols) {
  Fixture f("int f(int x) { switch(x) { case 1: break; default: x=0; } try { "
            "if(x) goto end; } catch(int v) { x=v; } catch(...) { x=-1; } end: "
            "return x; }");
  auto values = query(f.file, "switchStmt().bind(\"node\")");
  ASSERT_EQ(values.size(), 1U);
  EXPECT_TRUE(values[0].node().switch_stmt().default_case().has_default_stmt());
  EXPECT_TRUE(values[0].node().switch_stmt().has_condition());
  auto tries = query(f.file, "cxxTryStmt().bind(\"node\")");
  ASSERT_EQ(tries.size(), 1U);
  ASSERT_EQ(tries[0].node().cxx_try_stmt().handlers_size(), 2);
  const auto &first =
      tries[0].node().cxx_try_stmt().handlers(0).cxx_catch_stmt();
  EXPECT_TRUE(first.has_exception_declaration());
  EXPECT_FALSE(first.is_catch_all());
  const auto &second =
      tries[0].node().cxx_try_stmt().handlers(1).cxx_catch_stmt();
  EXPECT_FALSE(second.has_exception_declaration());
  EXPECT_TRUE(second.is_catch_all());
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
  EXPECT_EQ(copied.availability_size(), 0);
  EXPECT_EQ(copied.supported_scopes_size(), 2);
}
TEST(StatementSemantics,
     ExpansionLimitsAreExplicitAndDoNotPoisonOtherBindings) {
  std::string expression = "1";
  for (unsigned i = 0; i < 60; ++i)
    expression += "+1";
  Fixture f("int f() { return " + expression + "; }");
  auto values = query(f.file, "binaryOperator().bind(\"node\")");
  ASSERT_EQ(values.size(), 60U);
  unsigned complete = 0, truncated = 0;
  for (const auto &binding : values) {
    ctk::match::v1::MatchBinding copy;
    EXPECT_TRUE(copy.ParseFromString(binding.SerializeAsString()));
    if (binding.is_complete())
      ++complete;
    for (const auto &entry : binding.availability())
      if (entry.state() == ctk::ast::v1::FIELD_STATE_TRUNCATED) {
        ++truncated;
        break;
      }
  }
  EXPECT_GT(complete, 0U);
  EXPECT_GT(truncated, 0U);
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
TEST(StatementSemantics, StructuralConstantsKeepNativeFieldIndices) {
  Fixture f("struct P { unsigned : 0; int value; }; template<auto V> constexpr "
            "auto constant() { return V; } constexpr auto out = constant<P{7}>();");
  auto values = query(f.file, "declRefExpr(to(decl().bind(\"node\")))");
  unsigned checked = 0;
  for (const auto &binding : values) {
    if (!binding.node().has_template_param_object_decl())
      continue;
    const auto &constant =
        binding.node().template_param_object_decl().value_as_constant();
    ASSERT_TRUE(constant.has_structure());
    ASSERT_EQ(constant.structure().field_values_size(), 1);
    EXPECT_EQ(constant.structure().field_values(0).field().name(), "value");
    EXPECT_EQ(
        constant.structure().field_values(0).value().integer().decimal_value(),
        "7");
    ++checked;
  }
  EXPECT_GT(checked, 0U);
}
} // namespace
} // namespace ctk::clang_layer
