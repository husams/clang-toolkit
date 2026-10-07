#include "ctk/clang/tooling.hpp"
#include "ctk/platform/temporary_directory.hpp"
#include "ast/v1/semantic.pb.h"
#include <gtest/gtest.h>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

namespace ctk::clang_layer {
namespace {
std::vector<ctk::match::v1::MatchBinding>
query_types(const std::string &source, const std::string &matcher,
            std::vector<std::string> arguments = {"-std=c++20"}) {
  ctk::platform::TemporaryDirectory directory("ctk-type-semantics");
  auto path = directory.path() / "fixture.cpp";
  { std::ofstream stream(path); stream << source; }
  auto engine = make_query_engine();
  std::vector<ctk::match::v1::MatchBinding> values;
  const auto result = engine->match(
      {path.string(), std::move(arguments), std::filesystem::current_path().string()},
      matcher, [] { return true; },
      [&](const IQueryEngine::Bindings &bindings) {
        const auto &value = bindings.at("type").value;
        // Copy through the wire while the native snapshot is still alive.
        ctk::match::v1::MatchBinding owned;
        EXPECT_TRUE(owned.ParseFromString(value.SerializeAsString()));
        values.push_back(std::move(owned));
      });
  EXPECT_TRUE(result.ok) << result.message;
  return values;
}

TEST(TypeSemantics, BoundQualifiedTypePreservesEveryQualifierAndPresence) {
  auto values = query_types("const volatile int * __restrict const p = nullptr;",
      "varDecl(hasName(\"p\"), hasType(qualType().bind(\"type\")))");
  ASSERT_EQ(values.size(), 1U);
  const auto &binding = values.front();
  ASSERT_TRUE(binding.has_qualified_type());
  const auto &qualified = binding.qualified_type();
  EXPECT_TRUE(qualified.qualifiers().is_const());
  ASSERT_TRUE(qualified.qualifiers().has_is_volatile());
  EXPECT_FALSE(qualified.qualifiers().is_volatile());
  ASSERT_TRUE(qualified.qualifiers().has_is_restrict());
  EXPECT_TRUE(qualified.qualifiers().is_restrict());
  ASSERT_TRUE(qualified.qualifiers().has_is_unaligned());
  EXPECT_FALSE(qualified.qualifiers().is_unaligned());
  EXPECT_TRUE(qualified.qualifiers().address_space().has_default_space());
  ASSERT_TRUE(qualified.type().has_pointer_type());
  const auto &pointee = qualified.type().pointer_type().pointee_type();
  EXPECT_TRUE(pointee.qualifiers().is_const());
  EXPECT_TRUE(pointee.qualifiers().is_volatile());
  EXPECT_FALSE(pointee.qualifiers().is_restrict());
  ASSERT_TRUE(pointee.type().has_builtin_type());
  EXPECT_EQ(pointee.type().builtin_type().kind(), ctk::ast::v1::BUILTIN_KIND_INT);
  const auto &info = pointee.type().builtin_type().info();
  ASSERT_TRUE(info.has_spelling());
  EXPECT_EQ(info.spelling(), "int");
  ASSERT_TRUE(info.has_canonical_spelling());
  EXPECT_EQ(info.canonical_spelling(), "int");
  ASSERT_TRUE(info.has_is_dependent());
  EXPECT_FALSE(info.is_dependent());
  ASSERT_TRUE(info.has_is_instantiation_dependent());
  EXPECT_FALSE(info.is_instantiation_dependent());
  ASSERT_TRUE(info.has_contains_unexpanded_parameter_pack());
  EXPECT_FALSE(info.contains_unexpanded_parameter_pack());
  EXPECT_TRUE(binding.is_complete());
}

TEST(TypeSemantics, RecordQualifierAvailabilityMatchesNativeVersion) {
  auto values = query_types("namespace named { struct Host {}; } named::Host object;",
                           "recordType(hasDeclaration(cxxRecordDecl(hasName(\"Host\")))).bind(\"type\")");
  ASSERT_FALSE(values.empty());
#if CTK_TEST_CLANG_VERSION_MAJOR >= 22
  bool found_qualified = false;
#endif
  for (const auto &binding : values) {
    ASSERT_TRUE(binding.node().has_record_type());
    const auto &record = binding.node().record_type();
    EXPECT_EQ(record.declaration().name(), "Host");
#if CTK_TEST_CLANG_VERSION_MAJOR >= 22
    ASSERT_TRUE(record.has_qualifier());
    if (record.qualifier().has_namespace_name()) {
      found_qualified = true;
      EXPECT_EQ(record.qualifier().namespace_name().declaration().name(), "named");
    } else {
      EXPECT_TRUE(record.qualifier().has_null_specifier());
    }
    EXPECT_TRUE(binding.is_complete());
    EXPECT_EQ(binding.availability_size(), 0);
#else
    EXPECT_FALSE(record.has_qualifier());
    EXPECT_FALSE(binding.is_complete());
    ASSERT_EQ(binding.availability_size(), 1);
    const auto &availability = binding.availability(0);
    EXPECT_EQ(availability.field_path(), "RecordType.qualifier");
    EXPECT_EQ(availability.state(), ctk::ast::v1::FIELD_STATE_UNAVAILABLE);
    EXPECT_EQ(availability.reason(),
              "this Clang version does not retain a qualifier on this type node");
#endif
  }
#if CTK_TEST_CLANG_VERSION_MAJOR >= 22
  EXPECT_TRUE(found_qualified);
#endif
}

TEST(TypeSemantics, ArraysPreserveExactSizeAndElementValues) {
  auto values = query_types("int values[17];", "constantArrayType().bind(\"type\")");
  ASSERT_FALSE(values.empty());
  const auto &array = values.front().node().constant_array_type();
  EXPECT_EQ(array.size().unsigned_decimal(), "17");
  EXPECT_GT(array.size().bit_width(), 0U);
  ASSERT_FALSE(array.size().little_endian_bits().empty());
  EXPECT_EQ(array.size().little_endian_bits().front(), '\x11');
  EXPECT_EQ(array.size_modifier(), ctk::ast::v1::ARRAY_SIZE_MODIFIER_NORMAL);
  ASSERT_TRUE(array.element_type().type().has_builtin_type());
  EXPECT_EQ(array.element_type().type().builtin_type().kind(), ctk::ast::v1::BUILTIN_KIND_INT);
  EXPECT_TRUE(array.index_qualifiers().has_is_restrict());
}

TEST(TypeSemantics, FunctionPrototypePreservesParametersFlagsAndExceptionSpec) {
  auto values = query_types("using Fn = int (*)(double, const int *) noexcept; Fn callback;",
      "functionProtoType().bind(\"type\")");
  ASSERT_FALSE(values.empty());
  bool found = false;
  for (const auto &value : values) {
    const auto &function = value.node().function_proto_type();
    if (function.parameter_types_size() != 2) continue;
    found = true;
    EXPECT_TRUE(function.has_is_variadic());
    EXPECT_FALSE(function.is_variadic());
    EXPECT_EQ(function.return_type().type().builtin_type().kind(), ctk::ast::v1::BUILTIN_KIND_INT);
    EXPECT_EQ(function.parameter_types(0).type().builtin_type().kind(), ctk::ast::v1::BUILTIN_KIND_DOUBLE);
    EXPECT_TRUE(function.parameter_types(1).type().pointer_type().pointee_type().qualifiers().is_const());
    EXPECT_EQ(function.ext_info().calling_convention(), ctk::ast::v1::FUNCTION_CALLING_CONVENTION_C);
    EXPECT_TRUE(function.ext_info().has_no_return());
    EXPECT_FALSE(function.ext_info().no_return());
    EXPECT_FALSE(function.ext_info().has_regparm());
    EXPECT_EQ(function.prototype_info().exception_specification(),
              ctk::ast::v1::EXCEPTION_SPECIFICATION_MS_BASIC_NOEXCEPT);
  }
  EXPECT_TRUE(found);
}

TEST(TypeSemantics, MemberFunctionPointersPreserveClassAndMethodQualifiers) {
  auto values = query_types("struct Host { long f(const int *) const & noexcept; };\n"
                           "long (Host::*member)(const int *) const & noexcept = &Host::f;",
                           "memberPointerType().bind(\"type\")");
  ASSERT_FALSE(values.empty());
  const auto &pointer = values.front().node().member_pointer_type();
  EXPECT_TRUE(pointer.is_member_function_pointer());
  const auto &pointee = pointer.pointee_type().type();
  ASSERT_TRUE(pointee.has_paren_type()) << pointee.DebugString();
  const auto &unwrapped = pointee.paren_type().inner_type().type();
  ASSERT_TRUE(unwrapped.has_function_proto_type()) << unwrapped.DebugString();
  const auto &function = unwrapped.function_proto_type();
  EXPECT_EQ(function.prototype_info().ref_qualifier(), ctk::ast::v1::REF_QUALIFIER_LVALUE);
  EXPECT_TRUE(function.prototype_info().type_qualifiers().is_const());
  EXPECT_EQ(function.return_type().type().builtin_type().kind(), ctk::ast::v1::BUILTIN_KIND_LONG);
  EXPECT_TRUE(pointer.has_class_qualifier());
}

TEST(TypeSemantics, TemplateArgumentsPreserveTypesAndIntegralSignedness) {
  auto values = query_types("template<class T, int N> struct Box {}; Box<long, -3> instance;",
      "recordType(hasDeclaration(cxxRecordDecl(hasName(\"Box\")))).bind(\"type\")");
  ASSERT_FALSE(values.empty());
  bool found = false;
  for (const auto &value : values) {
    const auto &type = value.node().record_type();
    if (type.specialization_arguments_size() != 2 ||
        !type.specialization_arguments(1).has_integral()) continue;
    found = true;
    EXPECT_EQ(type.template_name().declaration().name(), "Box");
    EXPECT_EQ(type.specialization_arguments(0).type().type().builtin_type().kind(), ctk::ast::v1::BUILTIN_KIND_LONG);
    EXPECT_FALSE(type.specialization_arguments(1).integral().value().is_unsigned());
    EXPECT_EQ(type.specialization_arguments(1).integral().value().decimal_value(), "-3");
  }
  EXPECT_TRUE(found);
}

TEST(TypeSemantics, SubstitutionPreservesParameterAndReplacementType) {
  auto values = query_types("template<class T> T identity(T value) { return value; }\n"
                           "int use() { return identity(3); }",
                           "substTemplateTypeParmType().bind(\"type\")");
  ASSERT_FALSE(values.empty());
  const auto &substitution = values.front().node().subst_template_type_parm_type();
  EXPECT_EQ(substitution.replacement_type().type().builtin_type().kind(), ctk::ast::v1::BUILTIN_KIND_INT);
  EXPECT_EQ(substitution.replaced_parameter().name(), "T");
  EXPECT_EQ(substitution.associated_declaration().name(), "identity");
  EXPECT_TRUE(substitution.has_parameter_index());
  EXPECT_EQ(substitution.parameter_index(), 0U);
  EXPECT_TRUE(substitution.has_is_final());
}

TEST(TypeSemantics, VectorDimensionsAndElementTypeSurviveAliasDesugaring) {
  auto values = query_types("typedef int Vec __attribute__((vector_size(16))); Vec value;",
                           "typedefDecl(hasName(\"Vec\")).bind(\"type\")");
  ASSERT_EQ(values.size(), 1U);
  ASSERT_TRUE(values.front().node().has_typedef_decl());
  const auto &underlying = values.front().node().typedef_decl().underlying_type().type();
  ASSERT_TRUE(underlying.has_vector_type()) << underlying.DebugString();
  const auto &vector = underlying.vector_type();
  EXPECT_EQ(vector.element_count(), 4U);
  EXPECT_EQ(vector.vector_kind(), ctk::ast::v1::VECTOR_KIND_GENERIC);
  EXPECT_EQ(vector.element_type().type().builtin_type().kind(), ctk::ast::v1::BUILTIN_KIND_INT);
}

TEST(TypeSemantics, BitIntegerTypesPreserveWidthBeyondNativeScalars) {
  auto values = query_types("unsigned _BitInt(73) wide;",
      "varDecl(hasName(\"wide\"), hasType(qualType().bind(\"type\")))");
  ASSERT_EQ(values.size(), 1U);
  ASSERT_TRUE(values.front().qualified_type().type().has_bit_int_type());
  const auto &type = values.front().qualified_type().type().bit_int_type();
  EXPECT_EQ(type.bit_width(), 73U);
  EXPECT_TRUE(type.is_unsigned());
}

TEST(TypeSemantics, DecltypeOwnsItsExpressionAndExactUnderlyingType) {
  auto values = query_types("int input; decltype(input) copy;", "decltypeType().bind(\"type\")");
  ASSERT_FALSE(values.empty());
  const auto &type = values.front().node().decltype_type();
  ASSERT_TRUE(type.underlying_expression().has_decl_ref_expr());
  EXPECT_EQ(type.underlying_expression().decl_ref_expr().declaration().name(), "input");
  EXPECT_EQ(type.underlying_type().type().builtin_type().kind(), ctk::ast::v1::BUILTIN_KIND_INT);
}

TEST(TypeSemantics, DependentArraysOwnTheirBoundExpressionAndTemplateElement) {
  auto values = query_types("template<class T, int N> struct Buffer { T values[N]; };",
                           "dependentSizedArrayType().bind(\"type\")");
  ASSERT_FALSE(values.empty());
  const auto &type = values.front().node().dependent_sized_array_type();
  EXPECT_EQ(type.element_type().type().template_type_parm_type().declaration().name(), "T");
  EXPECT_EQ(type.size_expression().decl_ref_expr().declaration().name(), "N");
  EXPECT_EQ(type.size_modifier(), ctk::ast::v1::ARRAY_SIZE_MODIFIER_NORMAL);
  EXPECT_TRUE(type.info().is_dependent());
}
} // namespace
} // namespace ctk::clang_layer
