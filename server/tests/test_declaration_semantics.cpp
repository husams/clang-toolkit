#include "ctk/clang/tooling.hpp"
#include "ctk/platform/temporary_directory.hpp"

#include <gtest/gtest.h>

#include <filesystem>
#include <fstream>
#include <memory>
#include <string>
#include <vector>

namespace ctk::clang_layer {
namespace {
namespace pb = ctk::ast::v1;

bool has_unrequested(const ctk::match::v1::MatchBinding &binding,
                     const std::string &suffix) {
  for (const auto &entry : binding.availability())
    if (entry.state() == pb::FIELD_STATE_UNREQUESTED &&
        entry.field_path().ends_with(suffix))
      return true;
  return false;
}

class DeclarationSemantics : public ::testing::Test {
protected:
  ctk::platform::TemporaryDirectory directory_{"ctk-declaration-semantics"};
  std::shared_ptr<IQueryEngine> engine_ = make_query_engine();

  std::vector<ctk::match::v1::MatchBinding>
  match(std::string source, std::string matcher,
        std::vector<std::string> extra_arguments = {},
        const std::string &binding_name = "node") {
    const auto path = directory_.path() / "fixture.cc";
    {
      std::ofstream output(path);
      output << source;
    }
    FileInput input{path.string(), {"-std=c++20"}, directory_.path().string()};
    input.compile_arguments.insert(input.compile_arguments.end(),
                                   extra_arguments.begin(),
                                   extra_arguments.end());
    std::vector<ctk::match::v1::MatchBinding> rows;
    const auto result = engine_->match(
        input, matcher + ".bind(\"node\")", [] { return true; },
        [&](const IQueryEngine::Bindings &bindings) {
          rows.push_back(bindings.at(binding_name).value);
        });
    EXPECT_TRUE(result.ok) << result.message;
    return rows;
  }
};

TEST_F(DeclarationSemantics, FunctionReportsImmediateFieldsAndUnrequestedChildren) {
  auto rows =
      match("constexpr int sum(const int value = 9) { return value + 2; }",
            "functionDecl(hasName(\"sum\"))");
  ASSERT_EQ(rows.size(), 1U);
  const auto &value = rows[0].node().function_decl();
  const auto &function = value.function();
  EXPECT_TRUE(function.is_constexpr());
  EXPECT_TRUE(function.is_this_declaration_a_definition());
  EXPECT_EQ(function.storage_class(), pb::STORAGE_CLASS_NONE);
  EXPECT_EQ(function.return_type().description().spelling(), "int");
  EXPECT_EQ(function.parameters_size(), 0);
  EXPECT_FALSE(function.has_body());
  EXPECT_FALSE(value.is_deleted());
  EXPECT_FALSE(value.is_defaulted());
  EXPECT_TRUE(rows[0].is_complete());
  bool parameters_unrequested = false;
  bool body_unrequested = false;
  for (const auto &availability : rows[0].availability()) {
    if (availability.state() != pb::FIELD_STATE_UNREQUESTED)
      continue;
    if (availability.field_path().ends_with("parameters"))
      parameters_unrequested = true;
    if (availability.field_path().ends_with("body"))
      body_unrequested = true;
  }
  EXPECT_TRUE(parameters_unrequested);
  EXPECT_TRUE(body_unrequested);
}

TEST_F(DeclarationSemantics,
       VariableCarriesQualifiersStorageAndRedeclarationInitializer) {
  auto rows = match("extern const int number; const int number = 17; "
                    "thread_local int local = 3;",
                    "varDecl(hasName(\"number\"))");
  ASSERT_EQ(rows.size(), 2U);
  for (const auto &row : rows) {
    const auto &variable = row.node().var_decl();
    EXPECT_TRUE(variable.variable()
                    .declarator()
                    .value()
                    .type()
                    .qualifiers()
                    .is_const());
    EXPECT_FALSE(variable.has_initializer_from_any_declaration());
    EXPECT_FALSE(variable.variable().has_initializer());
    EXPECT_EQ(variable.tls_kind(), pb::DECL_VARIABLE_TLS_KIND_NONE);
    EXPECT_EQ(variable.initialization_style(),
              pb::DECL_VARIABLE_INITIALIZATION_STYLE_C);
    EXPECT_TRUE(has_unrequested(row, "VarDecl.initializer_from_any_declaration"));
  }
  EXPECT_FALSE(rows[0].node().var_decl().variable().has_initializer());
  EXPECT_FALSE(rows[1].node().var_decl().variable().has_initializer());
  EXPECT_TRUE(rows[0].is_complete());
  EXPECT_TRUE(rows[1].is_complete());
  rows = match("thread_local int local = 3;", "varDecl(hasName(\"local\"))");
  ASSERT_EQ(rows.size(), 1U);
  EXPECT_EQ(rows[0].node().var_decl().tls_kind(),
            pb::DECL_VARIABLE_TLS_KIND_DYNAMIC);
}

TEST_F(DeclarationSemantics,
       ParameterDefaultExpressionIsReportedAsUnrequested) {
  const auto rows = match(
      "template<class T> int function(int value = sizeof(T)) { return value; }"
      "int use() { return function<int>(4); }",
      "parmVarDecl(hasName(\"value\"))");
  ASSERT_EQ(rows.size(), 2U);
  for (const auto &row : rows) {
    const auto &parameter = row.node().parm_var_decl();
    EXPECT_FALSE(parameter.has_default_argument());
    EXPECT_TRUE(row.is_complete());
    bool unrequested = false;
    for (const auto &entry : row.availability())
      unrequested |= entry.state() == pb::FIELD_STATE_UNREQUESTED &&
                     entry.field_path().ends_with("default_argument");
    EXPECT_TRUE(unrequested);
  }
}

TEST_F(DeclarationSemantics, FieldBitWidthAndInitializerAreUnrequestedChildren) {
  auto rows = match("struct Bits { mutable unsigned code : 3 = 5; };",
                    "fieldDecl(hasName(\"code\"))");
  ASSERT_EQ(rows.size(), 1U);
  const auto &field = rows[0].node().field_decl();
  EXPECT_TRUE(field.is_mutable());
  EXPECT_TRUE(field.is_bit_field());
  EXPECT_FALSE(field.is_anonymous_struct_or_union());
  EXPECT_FALSE(field.has_bit_width());
  EXPECT_FALSE(field.has_in_class_initializer());
  EXPECT_TRUE(has_unrequested(rows[0], "bit_width"));
  EXPECT_TRUE(has_unrequested(rows[0], "in_class_initializer"));
  EXPECT_TRUE(rows[0].is_complete());
}

TEST_F(DeclarationSemantics, ConstructorsCarryTargetsAndExplicitValue) {
  auto rows = match(
      "struct Box { int value; explicit(true) Box(int n) : value(n) {} };",
      "cxxConstructorDecl(unless(isImplicit()))");
  ASSERT_EQ(rows.size(), 1U);
  const auto &constructor = rows[0].node().cxx_constructor_decl();
  EXPECT_TRUE(constructor.is_explicit());
  EXPECT_TRUE(constructor.is_explicit_specifier_value());
  EXPECT_FALSE(constructor.has_explicit_specifier_expression());
  EXPECT_FALSE(constructor.is_converting_constructor());
  EXPECT_FALSE(constructor.is_copy_constructor());
  EXPECT_FALSE(constructor.is_move_constructor());
  EXPECT_EQ(constructor.initializers_size(), 0);
  EXPECT_TRUE(has_unrequested(rows[0], "initializers"));
  EXPECT_TRUE(has_unrequested(rows[0], "explicit_specifier_expression"));
  EXPECT_TRUE(rows[0].is_complete());
}

TEST_F(DeclarationSemantics, MethodSymbolPreservesCvRefAndOverriddenSignature) {
  auto rows =
      match("struct Base { virtual int get(int n) const & noexcept = 0; };"
            "struct Derived : Base { int get(int n) const & noexcept override "
            "{ return n; } };",
            "cxxMethodDecl(hasName(\"Derived::get\"))");
  ASSERT_EQ(rows.size(), 1U);
  const auto &method = rows[0].node().cxx_method_decl().method();
  EXPECT_TRUE(method.is_virtual());
  EXPECT_TRUE(method.is_const());
  EXPECT_FALSE(method.is_volatile());
  EXPECT_EQ(method.ref_qualifier(), pb::REF_QUALIFIER_LVALUE);
  EXPECT_EQ(method.overridden_methods_size(), 0);
  EXPECT_TRUE(rows[0].is_complete());
}

TEST_F(DeclarationSemantics,
       RecordDefinitionBasesAndMembersDoNotExpandSymbols) {
  auto rows = match("struct Base {}; struct Derived : virtual protected Base { "
                    "int field; friend void friend_fn(); };",
                    "cxxRecordDecl(hasName(\"Derived\"), isDefinition())");
  ASSERT_EQ(rows.size(), 1U);
  const auto &record = rows[0].node().cxx_record_decl();
  EXPECT_EQ(record.record().tag().tag_kind(), pb::TAG_KIND_STRUCT);
  EXPECT_TRUE(record.record().tag().is_complete_definition());
  EXPECT_EQ(record.record().tag().type_declaration().declared_type().payload_case(),
            pb::TypeValue::PAYLOAD_NOT_SET);
  EXPECT_EQ(record.definition_bases_size(), 0);
  EXPECT_EQ(record.friends_size(), 0);
  EXPECT_EQ(record.record().members_size(), 0);
  EXPECT_TRUE(has_unrequested(rows[0], "definition_bases"));
  EXPECT_TRUE(has_unrequested(rows[0], "friends"));
  EXPECT_TRUE(has_unrequested(rows[0], "members"));
  EXPECT_FALSE(record.is_lambda());
  EXPECT_TRUE(rows[0].is_complete());
}

TEST_F(DeclarationSemantics, EnumValueRetainsValueAndOmitsInitializerChild) {
  auto rows = match("enum class Shade : long long { dark = -7, bright = 12 };",
                    "enumConstantDecl(hasName(\"dark\"))");
  ASSERT_EQ(rows.size(), 1U);
  const auto &constant = rows[0].node().enum_constant_decl();
  EXPECT_EQ(constant.evaluated_value().decimal_value(), "-7");
  EXPECT_FALSE(constant.evaluated_value().is_unsigned());
  EXPECT_FALSE(constant.has_initializer());
  EXPECT_TRUE(rows[0].is_complete());
  rows = match("enum class Shade : long long { dark = -7 };",
               "enumDecl(hasName(\"Shade\"))");
  ASSERT_EQ(rows.size(), 1U);
  const auto &enumeration = rows[0].node().enum_decl();
  EXPECT_TRUE(enumeration.is_scoped());
  EXPECT_TRUE(enumeration.is_fixed());
  EXPECT_EQ(enumeration.integer_type().type().payload_case(),
            pb::TypeValue::PAYLOAD_NOT_SET);
  EXPECT_TRUE(rows[0].is_complete());
}

TEST_F(DeclarationSemantics,
       TemplatesCarryDefaultsParametersAndIntegralSpecialization) {
  auto rows = match("template<class T = int, int N = 4> struct Array { T "
                    "data[N]; }; Array<long, 7> a;",
                    "classTemplateSpecializationDecl(hasName(\"Array\"))");
  ASSERT_EQ(rows.size(), 1U);
  const auto &specialization =
      rows[0].node().class_template_specialization_decl();
  EXPECT_EQ(specialization.template_arguments_size(), 0);
  EXPECT_EQ(specialization.specialized_template().name(), "Array");
  EXPECT_EQ(specialization.specialization_kind(),
            pb::DECL_TEMPLATE_SPECIALIZATION_KIND_IMPLICIT_INSTANTIATION);
  EXPECT_TRUE(rows[0].is_complete());
  rows =
      match("template<class T = int, int N = 4> struct Array { T data[N]; };",
            "classTemplateDecl(hasName(\"Array\"))");
  ASSERT_EQ(rows.size(), 1U);
  const auto &parameters =
      rows[0].node().class_template_decl().template_parameters();
  EXPECT_EQ(parameters.parameters_size(), 0);
  EXPECT_TRUE(rows[0].is_complete());
  EXPECT_TRUE(rows[0].is_complete());
}

TEST_F(DeclarationSemantics,
       TemplateTypeConstraintsAndRequiresClauseUseTypedChildren) {
  auto rows = match(
      "template<class T> concept Number = sizeof(T) > 0;"
      "template<Number T> requires Number<T> T identity(T x) { return x; }",
      "templateTypeParmDecl(hasName(\"T\"), "
      "hasParent(functionTemplateDecl()))");
  ASSERT_EQ(rows.size(), 1U);
  const auto &parameter = rows[0].node().template_type_parm_decl();
  ASSERT_TRUE(parameter.has_type_constraint());
  EXPECT_EQ(parameter.type_constraint().concept_reference().name().identifier(),
            "Number");
  EXPECT_FALSE(parameter.type_constraint().has_immediately_declared_constraint());
  EXPECT_TRUE(has_unrequested(rows[0],
                             "TypeConstraint.immediately_declared_constraint"));
  EXPECT_TRUE(rows[0].is_complete());
  rows = match("template<class T> concept Number = sizeof(T) > 0;",
               "conceptDecl(hasName(\"Number\"))");
  ASSERT_EQ(rows.size(), 1U);
  const auto &concept_value = rows[0].node().concept_decl();
  EXPECT_TRUE(concept_value.has_definition());
  EXPECT_TRUE(concept_value.is_type_concept());
  EXPECT_FALSE(concept_value.has_constraint_expression());
  EXPECT_TRUE(rows[0].is_complete());
}

TEST_F(DeclarationSemantics,
       UsingDeclarationsPreserveTargetsAndNamespaceAlias) {
  auto rows = match("namespace original { int target; } namespace alias = "
                    "original; using alias::target;",
                    "usingDecl()");
  ASSERT_EQ(rows.size(), 1U);
  const auto &using_value = rows[0].node().using_decl();
  EXPECT_EQ(using_value.shadows_size(), 0);
  EXPECT_TRUE(has_unrequested(rows[0], "UsingDecl.shadows"));
  EXPECT_EQ(using_value.name().identifier(), "target");
  EXPECT_FALSE(using_value.has_typename());
  EXPECT_FALSE(using_value.is_access_declaration());
  rows = match("namespace original {} namespace alias = original;",
               "namespaceAliasDecl()");
  ASSERT_EQ(rows.size(), 1U);
  EXPECT_EQ(
      rows[0].node().namespace_alias_decl().namespace_declaration().name(),
      "original");
  EXPECT_EQ(rows[0].node().namespace_alias_decl().aliased_namespace().name(),
            "original");
}

TEST_F(DeclarationSemantics,
       ConstrainedNonTypeParameterPreservesConceptLookupAndQualifier) {
  auto rows = match(
      "namespace traits { template<class T> concept Number = sizeof(T) > 0; }"
      "template<traits::Number auto N> struct Value {};",
      "nonTypeTemplateParmDecl(hasName(\"N\"))");
  ASSERT_EQ(rows.size(), 1U);
  const auto &parameter = rows[0].node().non_type_template_parm_decl();
  ASSERT_TRUE(parameter.has_type_constraint());
  EXPECT_EQ(parameter.type_constraint().concept_reference().name().identifier(),
            "Number");
  EXPECT_FALSE(parameter.type_constraint().has_immediately_declared_constraint());
  EXPECT_TRUE(has_unrequested(rows[0],
                             "TypeConstraint.immediately_declared_constraint"));
  EXPECT_TRUE(rows[0].is_complete());
}

TEST_F(DeclarationSemantics, StructuredBindingCarriesItsActualExpression) {
  auto rows = match("int data[2] = {3,4}; auto &[first, second] = data;",
                    "decompositionDecl(hasAnyBinding("
                    "bindingDecl(hasName(\"first\")).bind(\"declaration\")))",
                    {}, "declaration");
  ASSERT_EQ(rows.size(), 1U);
  const auto &binding = rows[0].node().binding_decl();
  EXPECT_EQ(binding.value().named().name().identifier(), "first");
  EXPECT_FALSE(binding.has_binding());
  EXPECT_FALSE(binding.has_holding_variable());
  EXPECT_TRUE(rows[0].is_complete());
}

TEST_F(DeclarationSemantics,
       StaticAssertAndFileAssemblyKeepOwnedExpressionValues) {
  auto rows =
      match("static_assert(2 + 3 == 5, \"sum\");", "staticAssertDecl()");
  ASSERT_EQ(rows.size(), 1U);
  const auto &assertion = rows[0].node().static_assert_decl();
  EXPECT_FALSE(assertion.is_failed());
  EXPECT_FALSE(assertion.has_assertion_expression());
  EXPECT_FALSE(assertion.has_message_expression());
  EXPECT_TRUE(rows[0].is_complete());
  rows = match("asm(\"\");", "decl()");
  unsigned assembly_declarations = 0;
  for (const auto &row : rows) {
    if (!row.node().has_file_scope_asm_decl())
      continue;
    ++assembly_declarations;
    const auto &assembly = row.node().file_scope_asm_decl().assembly_string();
    EXPECT_EQ(assembly.payload_case(), pb::ExpressionValue::PAYLOAD_NOT_SET);
  }
  EXPECT_EQ(assembly_declarations, 1U);
}

TEST_F(DeclarationSemantics,
       AttributesReportTheirConcreteClassAndUnavailableArguments) {
  auto rows = match("[[deprecated(\"use fresh\")]] int old;",
                    "varDecl(hasName(\"old\"))");
  ASSERT_EQ(rows.size(), 1U);
  const auto &info = rows[0]
                         .node()
                         .var_decl()
                         .variable()
                         .declarator()
                         .value()
                         .named()
                         .declaration();
  EXPECT_EQ(info.attributes_size(), 0);
  EXPECT_TRUE(has_unrequested(rows[0], "DeclInfo.attributes"));
  EXPECT_TRUE(rows[0].is_complete());
}

TEST_F(DeclarationSemantics,
       TypeAliasesAndTemplateAliasPreserveWrittenUnderlyingType) {
  auto rows = match("typedef const int Count; using Ref = Count &;",
                    "typeAliasDecl(hasName(\"Ref\"))");
  ASSERT_EQ(rows.size(), 1U);
  const auto &alias = rows[0].node().type_alias_decl();
  EXPECT_EQ(alias.type_declaration().named().name().identifier(), "Ref");
  EXPECT_EQ(alias.underlying_type().description().spelling(), "Count &");
  EXPECT_EQ(alias.underlying_type().type().payload_case(),
            pb::TypeValue::PAYLOAD_NOT_SET);
  EXPECT_TRUE(rows[0].is_complete());
  rows = match("template<class T> using Pointer = T *;",
               "typeAliasTemplateDecl(hasName(\"Pointer\"))");
  ASSERT_EQ(rows.size(), 1U);
  const auto &template_alias = rows[0].node().type_alias_template_decl();
  EXPECT_FALSE(template_alias.has_templated_declaration());
  EXPECT_EQ(template_alias.template_parameters().parameters_size(), 0);
  EXPECT_TRUE(rows[0].is_complete());
}

TEST_F(DeclarationSemantics,
       PartialSpecializationsKeepParameterAndPatternTypes) {
  auto rows = match(
      "template<class T> struct Box {}; template<class T> struct Box<T *> {};",
      "classTemplatePartialSpecializationDecl()");
  ASSERT_EQ(rows.size(), 1U);
  const auto &partial =
      rows[0].node().class_template_partial_specialization_decl();
  EXPECT_EQ(partial.template_arguments_size(), 0);
  EXPECT_EQ(partial.template_parameters().parameters_size(), 0);
  EXPECT_EQ(partial.specialized_template().name(), "Box");
  EXPECT_EQ(partial.specialized_template_or_partial().name(), "Box");
}

TEST_F(DeclarationSemantics,
       TemplateTemplateParameterKeepsItsNestedListAndDefault) {
  auto rows = match("template<class> struct Box {}; template<template<class> "
                    "class C = Box> struct Owner {};",
                    "templateTemplateParmDecl(hasName(\"C\"))");
  ASSERT_EQ(rows.size(), 1U);
  const auto &parameter = rows[0].node().template_template_parm_decl();
  EXPECT_EQ(parameter.depth(), 0U);
  EXPECT_EQ(parameter.position(), 0U);
  EXPECT_FALSE(parameter.is_parameter_pack());
  EXPECT_EQ(parameter.template_parameters().parameters_size(), 0);
  ASSERT_TRUE(parameter.has_default_argument());
  ASSERT_TRUE(parameter.default_argument().has_template_name());
  const auto &template_name = parameter.default_argument().template_name();
  const auto &underlying = template_name.has_qualified()
                               ? template_name.qualified().unqualified()
                               : template_name;
  EXPECT_EQ(underlying.declaration().name(), "Box")
      << template_name.DebugString();
  EXPECT_TRUE(rows[0].is_complete());
}

TEST_F(DeclarationSemantics, NamespaceOwnsDeclarationsAndOriginalScopeSymbol) {
  auto rows = match("inline namespace version { int number = 8; } namespace "
                    "version { void fn(); }",
                    "namespaceDecl(hasName(\"version\"))");
  ASSERT_EQ(rows.size(), 2U);
  for (const auto &row : rows) {
    const auto &name_space = row.node().namespace_decl();
    EXPECT_TRUE(name_space.is_inline());
    EXPECT_FALSE(name_space.is_anonymous());
    EXPECT_FALSE(name_space.has_original_namespace());
    EXPECT_TRUE(has_unrequested(row, "NamespaceDecl.original_namespace"));
    EXPECT_EQ(name_space.declarations_size(), 0);
    EXPECT_TRUE(row.is_complete());
  }
}

TEST_F(DeclarationSemantics, BlocksOwnParametersCapturesAndTheirSignature) {
  auto rows = match("void use() { int captured = 4; int (^block)(int) = ^(int "
                    "n) { return n + captured; }; }",
                    "blockDecl()", {"-fblocks"});
  ASSERT_EQ(rows.size(), 1U);
  const auto &block = rows[0].node().block_decl();
  EXPECT_EQ(block.parameters_size(), 0);
  EXPECT_EQ(block.captures_size(), 0);
  EXPECT_FALSE(block.has_body());
  EXPECT_FALSE(block.is_variadic());
  EXPECT_TRUE(rows[0].is_complete());
}

TEST_F(DeclarationSemantics, ConditionalConversionRetainsExplicitExpression) {
  auto rows = match("struct Value { explicit(false) operator bool() const { "
                    "return true; } };",
                    "cxxConversionDecl()");
  ASSERT_EQ(rows.size(), 1U);
  const auto &conversion = rows[0].node().cxx_conversion_decl();
  EXPECT_FALSE(conversion.is_explicit());
  EXPECT_FALSE(conversion.is_explicit_specifier_value());
  EXPECT_FALSE(conversion.has_explicit_specifier_expression());
  EXPECT_TRUE(conversion.method().is_const());
  EXPECT_TRUE(rows[0].is_complete());
}

TEST_F(DeclarationSemantics,
       VariableTemplateSpecializationKeepsTypedArguments) {
  auto rows = match(
      "template<class T> constexpr T count = T(4); long value = count<long>;",
      "declRefExpr(to(varDecl(hasName(\"count\"), isTemplateInstantiation())"
      ".bind(\"declaration\")))",
      {}, "declaration");
  ASSERT_EQ(rows.size(), 1U);
  const auto &specialization =
      rows[0].node().var_template_specialization_decl();
  EXPECT_EQ(specialization.template_arguments_size(), 0);
  EXPECT_EQ(specialization.specialized_template().name(), "count");
  EXPECT_TRUE(specialization.variable().is_constexpr());
  EXPECT_TRUE(rows[0].is_complete());
}

TEST_F(DeclarationSemantics,
       LabelOwnsStatementWithoutRecursingThroughGotoSymbols) {
  auto rows = match("void function() { goto done; done: return; }",
                    "labelStmt(hasDeclaration("
                    "labelDecl(hasName(\"done\")).bind(\"declaration\")))",
                    {}, "declaration");
  ASSERT_EQ(rows.size(), 1U);
  const auto &label = rows[0].node().label_decl();
  EXPECT_FALSE(label.has_statement());
  EXPECT_TRUE(rows[0].is_complete());
  EXPECT_FALSE(label.is_gnu_local());
  EXPECT_FALSE(label.named().declaration().has_containing_scope());
  EXPECT_TRUE(has_unrequested(rows[0], "DeclInfo.containing_scope"));
}

} // namespace
} // namespace ctk::clang_layer
