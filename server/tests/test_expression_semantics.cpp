#include "ast/v1/node.pb.h"
#include "ctk/clang/tooling.hpp"
#include "ctk/platform/temporary_directory.hpp"
#include <filesystem>
#include <fstream>
#include <functional>
#include <gtest/gtest.h>
#include <string>

namespace ctk::clang_layer {
namespace {
class ExpressionFixture {
public:
  ctk::platform::TemporaryDirectory directory{"ctk-expression-fields"};
  std::filesystem::path path = directory.path() / "fixture.cc";
  std::shared_ptr<IQueryEngine> engine = make_query_engine();
  explicit ExpressionFixture(const std::string &source) {
    std::ofstream(path) << source;
  }
  std::size_t
  query(const std::string &matcher,
        const std::function<void(const ctk::match::v1::MatchBinding &)> &check,
        const std::string &standard = "-std=c++20") {
    std::size_t count = 0;
    auto result = engine->match(
        {path.string(), {standard}, std::filesystem::current_path().string()},
        matcher + ".bind(\"value\")", [] { return true; },
        [&](const IQueryEngine::Bindings &bindings) {
          ++count;
          check(bindings.at("value").value);
        });
    EXPECT_TRUE(result.ok) << result.message;
    return count;
  }
};

TEST(ExpressionSemantics, OwnsNestedOperatorsAndPreservesComputationTypes) {
  ExpressionFixture fixture{"int run(int x) { x += 2; return -(x + 3); }"};
  EXPECT_EQ(
      fixture.query(
          "binaryOperator(hasOperatorName(\"+=\"))",
          [](const auto &binding) {
            const auto &node = binding.node().compound_assign_operator();
            EXPECT_EQ(node.opcode(), ctk::ast::v1::BINARY_OPCODE_ADD_ASSIGN);
            EXPECT_EQ(node.left().decl_ref_expr().declaration().name(), "x");
            EXPECT_EQ(node.right().integer_literal().value().unsigned_decimal(),
                      "2");
            EXPECT_TRUE(node.has_computation_lhs_type());
            EXPECT_TRUE(node.has_computation_result_type());
            EXPECT_TRUE(node.info().has_value_category());
          }),
      1U);
  EXPECT_EQ(fixture.query("unaryOperator(hasOperatorName(\"-\"))",
                          [](const auto &binding) {
                            const auto &node = binding.node().unary_operator();
                            EXPECT_EQ(node.opcode(),
                                      ctk::ast::v1::UNARY_OPCODE_MINUS);
                            EXPECT_TRUE(node.has_is_postfix());
                            EXPECT_FALSE(node.is_postfix());
                            ASSERT_TRUE(node.operand().has_paren_expr());
                            EXPECT_EQ(node.operand()
                                          .paren_expr()
                                          .subexpression()
                                          .binary_operator()
                                          .opcode(),
                                      ctk::ast::v1::BINARY_OPCODE_ADD);
                          }),
            1U);
}

TEST(ExpressionSemantics, PreservesFloatingBitsAndEmbeddedNullStringBytes) {
  ExpressionFixture fixture{
      "double number() { return 1.5; } const char text[] = \"a\\0b\";"};
  EXPECT_EQ(fixture.query(
                "floatLiteral()",
                [](const auto &binding) {
                  const auto &node = binding.node().floating_literal();
                  EXPECT_EQ(node.value().semantics(),
                            ctk::ast::v1::FLOATING_SEMANTICS_IEEE_DOUBLE);
                  EXPECT_EQ(node.value().bit_pattern().bit_width(), 64U);
                  EXPECT_EQ(
                      node.value().bit_pattern().little_endian_bits().size(),
                      8U);
                  EXPECT_TRUE(node.is_exact());
                }),
            1U);
  EXPECT_EQ(fixture.query("stringLiteral()",
                          [](const auto &binding) {
                            const auto &node = binding.node().string_literal();
                            EXPECT_EQ(node.value(), std::string("a\0b", 3));
                            EXPECT_EQ(node.code_unit_count(), 3U);
                            EXPECT_EQ(node.code_unit_width(), 8U);
                            EXPECT_EQ(
                                node.literal_kind(),
                                ctk::ast::v1::STRING_LITERAL_KIND_ORDINARY);
                          }),
            1U);
}

TEST(ExpressionSemantics, PreservesQualifiedObjectAndDerivedMemberCallFields) {
  ExpressionFixture fixture{"struct Box { int get(int n) const { return n; } "
                            "}; int run(const Box &b) { return b.get(7); }"};
  EXPECT_EQ(
      fixture.query("callExpr()",
                    [](const auto &binding) {
                      ASSERT_TRUE(binding.node().has_cxx_member_call_expr());
                      const auto &node = binding.node().cxx_member_call_expr();
                      EXPECT_EQ(node.method_declaration().name(), "get");
                      EXPECT_EQ(node.record_declaration().name(), "Box");
                      EXPECT_EQ(node.call().direct_callee().name(), "get");
                      ASSERT_EQ(node.call().arguments_size(), 1);
                      EXPECT_EQ(node.call()
                                    .arguments(0)
                                    .integer_literal()
                                    .value()
                                    .unsigned_decimal(),
                                "7");
                      EXPECT_TRUE(node.object_type().qualifiers().is_const());
                      EXPECT_EQ(node.implicit_object_argument()
                                    .decl_ref_expr()
                                    .declaration()
                                    .name(),
                                "b");
                    }),
      1U);
}

TEST(ExpressionSemantics, PreservesExplicitCastTypeAndFiniteBasePath) {
  ExpressionFixture fixture{
      "struct Base {}; struct Derived : Base {}; Base *run(Derived *p) { "
      "return static_cast<Base *>(p); }"};
  EXPECT_EQ(fixture.query(
                "cxxStaticCastExpr()",
                [](const auto &binding) {
                  const auto &node = binding.node().cxx_static_cast_expr();
                  EXPECT_EQ(node.cast().kind(), ctk::ast::v1::CAST_KIND_NO_OP);
                  ASSERT_TRUE(node.cast().operand().has_implicit_cast_expr());
                  const auto &conversion =
                      node.cast().operand().implicit_cast_expr().cast();
                  EXPECT_EQ(conversion.kind(),
                            ctk::ast::v1::CAST_KIND_DERIVED_TO_BASE);
                  ASSERT_EQ(conversion.base_path_size(), 1);
                  EXPECT_FALSE(conversion.base_path(0).is_virtual());
                  EXPECT_TRUE(node.has_target_type());
                  EXPECT_TRUE(node.cast().has_operand());
                }),
            1U);
}

TEST(ExpressionSemantics, KeepsRethrowAbsenceAndLiteralFalsePresence) {
  ExpressionFixture fixture{
      "bool flag() { return false; } void fail() { throw; }"};
  EXPECT_EQ(fixture.query("cxxBoolLiteral()",
                          [](const auto &binding) {
                            const auto &node =
                                binding.node().cxx_bool_literal_expr();
                            EXPECT_TRUE(node.has_value());
                            EXPECT_FALSE(node.value());
                          }),
            1U);
  EXPECT_EQ(fixture.query("cxxThrowExpr()",
                          [](const auto &binding) {
                            const auto &node = binding.node().cxx_throw_expr();
                            EXPECT_TRUE(node.is_rethrow());
                            EXPECT_FALSE(node.has_operand());
                          }),
            1U);
}

TEST(ExpressionSemantics, CapturesLambdaVariablesAndTheirInitializers) {
  ExpressionFixture fixture{"int run(int x) { auto f = [x, &y = x]() mutable { "
                            "return x + y; }; return f(); }"};
  EXPECT_EQ(
      fixture.query("lambdaExpr()",
                    [](const auto &binding) {
                      const auto &node = binding.node().lambda_expr();
                      EXPECT_TRUE(node.has_closure_class());
                      EXPECT_EQ(node.call_operator().name(), "operator()");
                      EXPECT_TRUE(node.is_mutable());
                      EXPECT_FALSE(node.is_generic_lambda());
                      ASSERT_EQ(node.captures_size(), 2);
                      EXPECT_EQ(node.captures(0).kind(),
                                ctk::ast::v1::LAMBDA_CAPTURE_KIND_BY_COPY);
                      EXPECT_EQ(node.captures(0).variable().name(), "x");
                      EXPECT_EQ(node.captures(1).kind(),
                                ctk::ast::v1::LAMBDA_CAPTURE_KIND_BY_REFERENCE);
                      EXPECT_EQ(node.captures(1).variable().name(), "y");
                      EXPECT_EQ(node.capture_initializers_size(), 2);
                    }),
      1U);
}

TEST(ExpressionSemantics, KeepsNewArrayAndPlacementArgumentSemantics) {
  ExpressionFixture fixture{
      "using size_t = decltype(sizeof(0)); void *operator new(size_t); void "
      "*operator new[](size_t); void operator delete(void *) noexcept; void "
      "operator delete[](void *) noexcept; int *run(int n) { return new "
      "int[n]{1}; }"};
  EXPECT_EQ(fixture.query(
                "cxxNewExpr()",
                [](const auto &binding) {
                  const auto &node = binding.node().cxx_new_expr();
                  EXPECT_TRUE(node.is_array());
                  EXPECT_FALSE(node.is_placement());
                  EXPECT_FALSE(node.is_global_new());
                  EXPECT_EQ(node.placement_arguments_size(), 0);
                  EXPECT_TRUE(node.has_array_size());
                  EXPECT_TRUE(node.has_initializer());
                  EXPECT_EQ(node.operator_new().name(), "operator new[]");
                  EXPECT_EQ(node.allocated_type().type().builtin_type().kind(),
                            ctk::ast::v1::BUILTIN_KIND_INT);
                }),
            1U);
}

TEST(ExpressionSemantics, SerializesRequiresRequirementsAndDependentPresence) {
  ExpressionFixture fixture{
      "template<class T> concept Valid = requires(T x) { typename "
      "T::value_type; x + x; requires sizeof(T) > 0; }; struct A { using "
      "value_type = int; }; static_assert(!Valid<A>);"};
  std::size_t requirements = 0;
  fixture.query("expr()", [&](const auto &binding) {
    if (!binding.node().has_requires_expr())
      return;
    ++requirements;
    const auto &node = binding.node().requires_expr();
    EXPECT_TRUE(node.has_body_declaration());
    ASSERT_EQ(node.requirements_size(), 3);
    EXPECT_TRUE(node.requirements(0).has_type());
    EXPECT_TRUE(node.requirements(1).has_expression());
    EXPECT_TRUE(node.requirements(2).has_nested());
    if (node.info().is_value_dependent())
      EXPECT_FALSE(node.has_is_satisfied());
  });
  EXPECT_GE(requirements, 1U);
}

TEST(ExpressionSemantics,
     PreservesOffsetArrayExpressionAndExactEvaluatedOffset) {
  ExpressionFixture fixture{"struct S { int values[4]; }; unsigned long run() "
                            "{ return __builtin_offsetof(S, values[2]); }"};
  std::size_t offsets = 0;
  fixture.query("expr()", [&](const auto &binding) {
    if (!binding.node().has_offset_of_expr())
      return;
    ++offsets;
    const auto &node = binding.node().offset_of_expr();
    ASSERT_EQ(node.components_size(), 2);
    EXPECT_EQ(node.components(0).field().name(), "values");
    EXPECT_TRUE(node.components(1).has_index_expression());
    EXPECT_EQ(node.byte_offset().unsigned_decimal(), "8");
  });
  EXPECT_EQ(offsets, 1U);
}

TEST(ExpressionSemantics, PreservesSignedConstantExpressionBits) {
  ExpressionFixture fixture{"enum E { negative = -7 };"};
  EXPECT_EQ(fixture.query(
                "constantExpr()",
                [](const auto &binding) {
                  const auto &node = binding.node().constant_expr();
                  ASSERT_TRUE(node.value().has_integer());
                  EXPECT_EQ(node.value().integer().decimal_value(), "-7");
                  EXPECT_FALSE(node.value().integer().is_unsigned());
                  EXPECT_EQ(node.value().integer().value().bit_width(), 32U);
                  EXPECT_EQ(node.result_kind(),
                            ctk::ast::v1::CONSTANT_EXPR_RESULT_SUCCEEDED);
                }),
            1U);
}

TEST(ExpressionSemantics, PreservesTypeTraitIdentityAndValue) {
  ExpressionFixture fixture{"bool flag() { return __is_same(int, int); }"};
  std::size_t traits = 0;
  fixture.query("expr()", [&](const auto &binding) {
    if (!binding.node().has_type_trait_expr())
      return;
    ++traits;
    const auto &node = binding.node().type_trait_expr();
    EXPECT_EQ(node.trait_name(), "IsSame");
    EXPECT_TRUE(node.trait_value());
    EXPECT_TRUE(node.has_trait_value());
    EXPECT_EQ(node.queried_types_size(), 2);
  });
  EXPECT_EQ(traits, 1U);
}

TEST(ExpressionSemantics, PreservesUndefinedShuffleMaskSentinel) {
  ExpressionFixture fixture{
      "using V = int __attribute__((vector_size(16))); V run(V a, V b) { "
      "return __builtin_shufflevector(a, b, -1, 0, 5, 3); }"};
  std::size_t shuffles = 0;
  fixture.query("expr()", [&](const auto &binding) {
    if (!binding.node().has_shuffle_vector_expr())
      return;
    ++shuffles;
    const auto &node = binding.node().shuffle_vector_expr();
    EXPECT_EQ(node.arguments_size(), 6);
    ASSERT_EQ(node.signed_shuffle_mask_size(), 4);
    EXPECT_EQ(node.signed_shuffle_mask(0), -1);
    EXPECT_EQ(node.signed_shuffle_mask(1), 0);
    EXPECT_EQ(node.signed_shuffle_mask(2), 5);
    EXPECT_EQ(node.signed_shuffle_mask(3), 3);
  });
  EXPECT_EQ(shuffles, 1U);
}
} // namespace
} // namespace ctk::clang_layer
