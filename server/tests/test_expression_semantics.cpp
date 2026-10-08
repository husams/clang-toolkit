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
bool has_unrequested(const ctk::match::v1::MatchBinding &binding,
                     const std::string &suffix) {
  for (const auto &entry : binding.availability())
    if (entry.state() == ctk::ast::v1::FIELD_STATE_UNREQUESTED &&
        entry.field_path().ends_with(suffix))
      return true;
  return false;
}

bool has_unrequested_exact(const ctk::match::v1::MatchBinding &binding,
                           const std::string &path) {
  for (const auto &entry : binding.availability())
    if (entry.state() == ctk::ast::v1::FIELD_STATE_UNREQUESTED &&
        entry.field_path() == path)
      return true;
  return false;
}

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
            EXPECT_FALSE(node.has_left());
            EXPECT_FALSE(node.has_right());
            EXPECT_TRUE(has_unrequested(binding, "left"));
            EXPECT_TRUE(has_unrequested(binding, "right"));
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
                            EXPECT_FALSE(node.has_operand());
                            EXPECT_TRUE(binding.is_complete());
                            EXPECT_TRUE(has_unrequested(binding, "operand"));
                          }),
            1U);
}

TEST(ExpressionSemantics,
     PreservesConcreteAndDependentConvertVectorTypesWithoutAborting) {
  ExpressionFixture fixture{
      "typedef int int4 __attribute__((vector_size(16)));\n"
      "int4 concrete(int4 value) {\n"
      "  return __builtin_convertvector(value, int4);\n"
      "}\n"
      "template<class D, class S> D dependent(S value) {\n"
      "  return __builtin_convertvector(value, D);\n"
      "}\n"
      "template<int N, class S> auto sized(S value) {\n"
      "  typedef int D __attribute__((vector_size(N)));\n"
      "  return __builtin_convertvector(value, D);\n"
      "}\n"
      "template<int N, class S> auto extSized(S value) {\n"
      "  typedef float D __attribute__((ext_vector_type(N)));\n"
      "  return __builtin_convertvector(value, D);\n"
      "}\n"};

  auto engine = fixture.engine;
  const auto check_conversion = [&](const std::string &function_name,
                                    const auto &check) {
    std::size_t matches = 0;
    const auto result = engine->match(
        {fixture.path.string(),
         {"-std=c++20"},
         std::filesystem::current_path().string()},
        "returnStmt(hasAncestor(functionDecl(hasName(\"" + function_name +
            "\"))), hasReturnValue(expr().bind(\"conversion\")))",
        [] { return true; },
        [&](const IQueryEngine::Bindings &row) {
          ++matches;
          check(row.at("conversion").value);
        });
    EXPECT_TRUE(result.ok) << result.message;
    EXPECT_EQ(matches, 1U);
  };

  check_conversion("concrete", [](const auto &binding) {
    const auto &conversion = binding.node().convert_vector_expr();
    ASSERT_TRUE(conversion.has_destination_element_type());
    ASSERT_TRUE(conversion.info().has_type());
    EXPECT_TRUE(conversion.destination_element_type().description().has_spelling());
    EXPECT_TRUE(conversion.info().type().description().has_spelling());
    EXPECT_TRUE(binding.is_complete());
  });

  check_conversion("dependent", [](const auto &binding) {
    const auto &conversion = binding.node().convert_vector_expr();
    EXPECT_FALSE(conversion.has_destination_element_type());
    EXPECT_TRUE(conversion.info().type().description().has_spelling());
    EXPECT_FALSE(binding.is_complete());
    bool unavailable = false;
    for (const auto &entry : binding.availability())
      unavailable |=
          entry.state() == ctk::ast::v1::FIELD_STATE_UNAVAILABLE &&
          entry.field_path().ends_with("destination_element_type");
    EXPECT_TRUE(unavailable);
  });

  const auto check_known_element = [](const auto &binding) {
    const auto &conversion = binding.node().convert_vector_expr();
    ASSERT_TRUE(conversion.has_destination_element_type());
    EXPECT_TRUE(conversion.destination_element_type().description().has_spelling());
    EXPECT_TRUE(binding.is_complete());
  };
  check_conversion("sized", [&](const auto &binding) {
    check_known_element(binding);
  });
  check_conversion("extSized", [&](const auto &binding) {
    check_known_element(binding);
  });

  // A bound declaration reports its direct facts and omits its body.
  std::size_t functions = 0;
  const auto result = engine->match(
      {fixture.path.string(),
       {"-std=c++20"},
       std::filesystem::current_path().string()},
      "functionDecl(hasName(\"dependent\")).bind(\"function\")",
      [] { return true; },
      [&](const IQueryEngine::Bindings &row) {
        ++functions;
        const auto &binding = row.at("function").value;
        ASSERT_TRUE(binding.node().has_function_decl());
        EXPECT_FALSE(binding.node().function_decl().function().has_body());
        EXPECT_TRUE(binding.is_complete());
        EXPECT_TRUE(has_unrequested(binding, "body"));
      });
  EXPECT_TRUE(result.ok) << result.message;
  EXPECT_EQ(functions, 1U);
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
                      EXPECT_EQ(node.call().arguments_size(), 0);
                      EXPECT_TRUE(has_unrequested_exact(
                          binding, "CallExprInfo.arguments"));
                      EXPECT_TRUE(node.object_type().qualifiers().is_const());
                      EXPECT_EQ(node.object_type().description().spelling(),
                                "const Box");
                      EXPECT_FALSE(node.has_implicit_object_argument());
                      EXPECT_TRUE(has_unrequested(binding, "implicit_object_argument"));
                      EXPECT_TRUE(binding.is_complete());
                    }),
      1U);
}

TEST(ExpressionSemantics, PreservesExplicitCastTypeAndAbsentBasePath) {
  ExpressionFixture fixture{
      "struct Base {}; struct Derived : Base {}; Base *run(Derived *p) { "
      "return static_cast<Base *>(p); }"};
  EXPECT_EQ(fixture.query(
                "cxxStaticCastExpr()",
                [](const auto &binding) {
                  const auto &node = binding.node().cxx_static_cast_expr();
                  EXPECT_EQ(node.cast().kind(), ctk::ast::v1::CAST_KIND_NO_OP);
                  EXPECT_FALSE(node.cast().has_operand());
                  EXPECT_TRUE(has_unrequested(binding, "operand"));
                  EXPECT_EQ(node.cast().base_path_size(), 0);
                  EXPECT_TRUE(node.has_target_type());
                  EXPECT_EQ(node.target_type().description().spelling(),
                            "Base *");
                  EXPECT_TRUE(binding.is_complete());
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
                      EXPECT_EQ(node.captures_size(), 0);
                      EXPECT_EQ(node.capture_initializers_size(), 0);
                      EXPECT_TRUE(has_unrequested(binding, "captures"));
                      EXPECT_TRUE(has_unrequested(binding, "capture_initializers"));
                      EXPECT_TRUE(binding.is_complete());
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
                  EXPECT_FALSE(node.has_array_size());
                  EXPECT_FALSE(node.has_initializer());
                  EXPECT_TRUE(has_unrequested(binding, "array_size"));
                  EXPECT_TRUE(has_unrequested(binding, "initializer"));
                  EXPECT_EQ(node.operator_new().name(), "operator new[]");
                  EXPECT_EQ(node.allocated_type().description().spelling(), "int");
                  EXPECT_TRUE(binding.is_complete());
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
    EXPECT_FALSE(node.has_body_declaration());
    EXPECT_EQ(node.requirements_size(), 0);
    EXPECT_TRUE(binding.is_complete());
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
    EXPECT_EQ(node.components_size(), 0);
    EXPECT_TRUE(has_unrequested_exact(binding, "OffsetOfExpr.components"));
    EXPECT_FALSE(node.has_byte_offset());
    EXPECT_TRUE(has_unrequested_exact(binding, "OffsetOfExpr.byte_offset"));
    EXPECT_TRUE(binding.is_complete());
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
    EXPECT_EQ(node.queried_types_size(), 0);
    EXPECT_TRUE(binding.is_complete());
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
    EXPECT_EQ(node.arguments_size(), 0);
    EXPECT_TRUE(has_unrequested_exact(binding, "ShuffleVectorExpr.arguments"));
    EXPECT_EQ(node.signed_shuffle_mask_size(), 0);
    EXPECT_EQ(node.shuffle_mask_size(), 0);
    EXPECT_TRUE(has_unrequested_exact(
        binding, "ShuffleVectorExpr.signed_shuffle_mask"));
    EXPECT_TRUE(
        has_unrequested_exact(binding, "ShuffleVectorExpr.shuffle_mask"));
  });
  EXPECT_EQ(shuffles, 1U);
}
} // namespace
} // namespace ctk::clang_layer
