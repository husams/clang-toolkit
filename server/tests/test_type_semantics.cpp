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
bool has_unrequested(const ctk::match::v1::MatchBinding &binding,
                     const std::string &suffix) {
  for (const auto &entry : binding.availability())
    if (entry.state() == ctk::ast::v1::FIELD_STATE_UNREQUESTED &&
        entry.field_path().ends_with(suffix))
      return true;
  return false;
}

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
  EXPECT_EQ(qualified.description().spelling(),
            "const volatile int *const __restrict");
  EXPECT_EQ(qualified.description().canonical_spelling(),
            "const volatile int *const __restrict");
  EXPECT_FALSE(qualified.description().is_dependent());
  EXPECT_EQ(qualified.type().payload_case(),
            ctk::ast::v1::TypeValue::PAYLOAD_NOT_SET);
  EXPECT_TRUE(binding.is_complete());
  EXPECT_TRUE(has_unrequested(binding, "QualType.type"));
}

TEST(TypeSemantics, BoundQualTypePreservesDescriptionAndOmitsNestedTypeValue) {
  auto values = query_types(
      "int *pointer;",
      "varDecl(hasName(\"pointer\"), hasType(qualType().bind(\"type\")))");
  ASSERT_EQ(values.size(), 1U);
  const auto &binding = values.front();
  ASSERT_TRUE(binding.has_qualified_type());
  const auto &qualified = binding.qualified_type();
  EXPECT_EQ(qualified.description().spelling(), "int *");
  EXPECT_EQ(qualified.description().canonical_spelling(), "int *");
  EXPECT_FALSE(qualified.description().is_dependent());
  EXPECT_EQ(qualified.type().payload_case(),
            ctk::ast::v1::TypeValue::PAYLOAD_NOT_SET);
  EXPECT_TRUE(has_unrequested(binding, "QualType.type"));
  EXPECT_TRUE(binding.is_complete());
}

TEST(TypeSemantics, RecordQualifierAvailabilityMatchesNativeVersion) {
  auto values = query_types("namespace named { struct Host {}; } named::Host object;",
                           "recordType(hasDeclaration(cxxRecordDecl(hasName(\"Host\")))).bind(\"type\")");
  ASSERT_FALSE(values.empty());
  for (const auto &binding : values) {
    ASSERT_TRUE(binding.node().has_record_type());
    const auto &record = binding.node().record_type();
    EXPECT_EQ(record.declaration().name(), "Host");
    EXPECT_FALSE(record.has_qualifier());
    EXPECT_TRUE(binding.is_complete());
    bool qualifier_unrequested = false;
    for (const auto &entry : binding.availability())
      qualifier_unrequested |=
          entry.state() == ctk::ast::v1::FIELD_STATE_UNREQUESTED &&
          entry.field_path().ends_with("qualifier");
    EXPECT_TRUE(qualifier_unrequested);
  }
}

TEST(TypeSemantics, ArraysPreserveExactSizeAndElementValues) {
  auto values = query_types("int values[17];",
      "varDecl(hasName(\"values\"), hasType(constantArrayType().bind(\"type\")))");
  ASSERT_EQ(values.size(), 1U);
  ASSERT_TRUE(values.front().node().has_constant_array_type());
  const auto &array = values.front().node().constant_array_type();
  EXPECT_EQ(array.size().unsigned_decimal(), "17");
  EXPECT_GT(array.size().bit_width(), 0U);
  ASSERT_FALSE(array.size().little_endian_bits().empty());
  EXPECT_EQ(array.size().little_endian_bits().front(), '\x11');
  EXPECT_EQ(array.size_modifier(), ctk::ast::v1::ARRAY_SIZE_MODIFIER_NORMAL);
  EXPECT_EQ(array.element_type().description().spelling(), "int");
  EXPECT_EQ(array.element_type().type().payload_case(),
            ctk::ast::v1::TypeValue::PAYLOAD_NOT_SET);
  EXPECT_TRUE(values.front().is_complete());
  EXPECT_TRUE(array.index_qualifiers().has_is_restrict());
}

TEST(TypeSemantics, ArraysSelectFixtureTypeAcrossTargetArchitectures) {
  for (const auto *target : {"x86_64-unknown-linux-gnu", "aarch64-unknown-linux-gnu"}) {
    SCOPED_TRACE(target);
    auto values = query_types("int decoy[1]; int values[17];",
        "varDecl(hasName(\"values\"), hasType(constantArrayType().bind(\"type\")))",
        {"-std=c++20", std::string("--target=") + target});
    ASSERT_EQ(values.size(), 1U);
    ASSERT_TRUE(values.front().node().has_constant_array_type());
    const auto &array = values.front().node().constant_array_type();
    EXPECT_EQ(array.size().unsigned_decimal(), "17");
    EXPECT_EQ(array.element_type().description().spelling(), "int");
    EXPECT_EQ(array.element_type().type().payload_case(),
              ctk::ast::v1::TypeValue::PAYLOAD_NOT_SET);
  }
}

TEST(TypeSemantics, FunctionPrototypePreservesParametersFlagsAndExceptionSpec) {
  auto values = query_types("using Fn = int (*)(double, const int *) noexcept; Fn callback;",
      "functionProtoType().bind(\"type\")");
  ASSERT_FALSE(values.empty());
  bool found = false;
  for (const auto &value : values) {
    if (!value.node().has_function_proto_type()) continue;
    found = true;
    const auto &function = value.node().function_proto_type();
    EXPECT_TRUE(function.has_is_variadic());
    EXPECT_FALSE(function.is_variadic());
    EXPECT_EQ(function.return_type().description().spelling(), "int");
    EXPECT_EQ(function.parameter_types_size(), 0);
    EXPECT_TRUE(has_unrequested(value, "parameter_types"));
    EXPECT_EQ(function.ext_info().calling_convention(), ctk::ast::v1::FUNCTION_CALLING_CONVENTION_C);
    EXPECT_TRUE(function.ext_info().has_no_return());
    EXPECT_FALSE(function.ext_info().no_return());
    EXPECT_FALSE(function.ext_info().has_regparm());
    EXPECT_EQ(function.prototype_info().exception_specification(),
              ctk::ast::v1::EXCEPTION_SPECIFICATION_MS_BASIC_NOEXCEPT);
    EXPECT_TRUE(value.is_complete());
  }
  EXPECT_TRUE(found);
}

TEST(TypeSemantics, MemberFunctionPointersPreserveMethodQualifiersAndOmitClassQualifier) {
  auto values = query_types("struct Host { long f(const int *) const & noexcept; };\n"
                           "long (Host::*member)(const int *) const & noexcept = &Host::f;",
                           "memberPointerType().bind(\"type\")");
  ASSERT_FALSE(values.empty());
  const auto &pointer = values.front().node().member_pointer_type();
  EXPECT_TRUE(pointer.is_member_function_pointer());
  const auto &spelling = pointer.pointee_type().description().spelling();
  EXPECT_NE(spelling.find("long"), std::string::npos);
  EXPECT_NE(spelling.find("const"), std::string::npos);
  EXPECT_EQ(pointer.pointee_type().type().payload_case(),
            ctk::ast::v1::TypeValue::PAYLOAD_NOT_SET);
  EXPECT_FALSE(pointer.has_class_qualifier());
  EXPECT_TRUE(has_unrequested(values.front(),
                              "MemberPointerType.class_qualifier"));
  EXPECT_TRUE(values.front().is_complete());
}

TEST(TypeSemantics, TemplateArgumentsPreserveTypesAndIntegralSignedness) {
  auto values = query_types("template<class T, int N> struct Box {}; Box<long, -3> instance;",
      "recordType(hasDeclaration(cxxRecordDecl(hasName(\"Box\")))).bind(\"type\")");
  ASSERT_FALSE(values.empty());
  bool found = false;
  for (const auto &value : values) {
    const auto &type = value.node().record_type();
    if (type.info().spelling().find("Box") == std::string::npos ||
        type.info().spelling().find("-3") == std::string::npos)
      continue;
    found = true;
    EXPECT_EQ(type.template_name().declaration().name(), "Box");
    EXPECT_EQ(type.specialization_arguments_size(), 0);
    EXPECT_TRUE(has_unrequested(value, "specialization_arguments"));
    EXPECT_TRUE(value.is_complete());
  }
  EXPECT_TRUE(found);
}

TEST(TypeSemantics, SubstitutionPreservesParameterAndReplacementType) {
  auto values = query_types("template<class T> T identity(T value) { return value; }\n"
                           "int use() { return identity(3); }",
                           "substTemplateTypeParmType().bind(\"type\")");
  ASSERT_FALSE(values.empty());
  const auto &substitution = values.front().node().subst_template_type_parm_type();
  EXPECT_EQ(substitution.replacement_type().description().spelling(), "int");
  EXPECT_EQ(substitution.replacement_type().type().payload_case(),
            ctk::ast::v1::TypeValue::PAYLOAD_NOT_SET);
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
  const auto &underlying = values.front().node().typedef_decl().underlying_type();
  EXPECT_TRUE(underlying.description().spelling().find("vector") !=
              std::string::npos);
  EXPECT_EQ(underlying.type().payload_case(),
            ctk::ast::v1::TypeValue::PAYLOAD_NOT_SET);
  EXPECT_TRUE(values.front().is_complete());
}

TEST(TypeSemantics, BitIntegerTypesPreserveWidthBeyondNativeScalars) {
  auto values = query_types("unsigned _BitInt(73) wide;",
      "varDecl(hasName(\"wide\"), hasType(qualType().bind(\"type\")))");
  ASSERT_EQ(values.size(), 1U);
  const auto &binding = values.front();
  const auto &qualified = binding.qualified_type();
  EXPECT_EQ(qualified.description().spelling(), "unsigned _BitInt(73)");
  EXPECT_EQ(qualified.description().canonical_spelling(), "unsigned _BitInt(73)");
  EXPECT_FALSE(qualified.description().is_dependent());
  EXPECT_EQ(qualified.type().payload_case(),
            ctk::ast::v1::TypeValue::PAYLOAD_NOT_SET);
  EXPECT_TRUE(has_unrequested(binding, "QualType.type"));
  EXPECT_TRUE(binding.is_complete());
}

TEST(TypeSemantics, DecltypeOwnsItsExpressionAndExactUnderlyingType) {
  auto values = query_types("int input; decltype(input) copy;", "decltypeType().bind(\"type\")");
  ASSERT_FALSE(values.empty());
  const auto &type = values.front().node().decltype_type();
  EXPECT_EQ(type.underlying_expression().payload_case(),
            ctk::ast::v1::ExpressionValue::PAYLOAD_NOT_SET);
  EXPECT_TRUE(has_unrequested(values.front(), "underlying_expression"));
  EXPECT_EQ(type.underlying_type().description().spelling(), "int");
  EXPECT_EQ(type.underlying_type().type().payload_case(),
            ctk::ast::v1::TypeValue::PAYLOAD_NOT_SET);
  EXPECT_TRUE(values.front().is_complete());
}

TEST(TypeSemantics, DependentArraysOwnTheirBoundExpressionAndTemplateElement) {
  auto values = query_types("template<class T, int N> struct Buffer { T values[N]; };",
                           "dependentSizedArrayType().bind(\"type\")");
  ASSERT_FALSE(values.empty());
  const auto &type = values.front().node().dependent_sized_array_type();
  EXPECT_EQ(type.element_type().description().spelling(), "T");
  EXPECT_EQ(type.element_type().type().payload_case(),
            ctk::ast::v1::TypeValue::PAYLOAD_NOT_SET);
  EXPECT_EQ(type.size_expression().payload_case(),
            ctk::ast::v1::ExpressionValue::PAYLOAD_NOT_SET);
  EXPECT_TRUE(has_unrequested(values.front(), "size_expression"));
  EXPECT_EQ(type.size_modifier(), ctk::ast::v1::ARRAY_SIZE_MODIFIER_NORMAL);
  EXPECT_TRUE(type.info().is_dependent());
}
} // namespace
} // namespace ctk::clang_layer
