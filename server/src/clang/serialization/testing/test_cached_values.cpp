#include "../declaration_helpers.hpp"
#include "../semantic_helpers.hpp"
#include <clang/AST/DeclTemplate.h>
#include <clang/Frontend/ASTUnit.h>
#include <clang/Tooling/Tooling.h>
#include <gtest/gtest.h>

namespace ctk::clang_layer::serialization::testing {
namespace {
bool has_unrequested(const ctk::match::v1::MatchBinding &binding,
                     const std::string &suffix) {
  for (const auto &entry : binding.availability())
    if (entry.state() == ctk::ast::v1::FIELD_STATE_UNREQUESTED &&
        entry.field_path().ends_with(suffix))
      return true;
  return false;
}

TEST(CachedValues, StructuralConstantChildrenAreUnrequested) {
  auto ast = clang::tooling::buildASTFromCodeWithArgs(
      "struct ArrayBox { int values[3]; }; "
      "union Choice { int integer; double real; }; "
      "template<auto V> struct Holder {}; "
      "Holder<ArrayBox{{1, 2}}> array_value; "
      "Holder<Choice{.integer = 9}> union_value;",
      {"-std=c++23"}, "fixture.cc", "ctk-test");
  ASSERT_TRUE(ast);
  auto &ast_context = ast->getASTContext();
  bool saw_array_record = false;
  bool saw_union = false;
  for (const auto *decl : ast_context.getTranslationUnitDecl()->decls()) {
    const auto *template_decl = llvm::dyn_cast<clang::ClassTemplateDecl>(decl);
    if (!template_decl)
      continue;
    for (const auto *specialization : template_decl->specializations()) {
      for (const auto &argument : specialization->getTemplateArgs().asArray()) {
        const clang::APValue *native_value = nullptr;
        clang::QualType native_type;
        if (argument.getKind() == clang::TemplateArgument::StructuralValue) {
          native_value = &argument.getAsStructuralValue();
          native_type = argument.getStructuralValueType();
        } else if (argument.getKind() == clang::TemplateArgument::Declaration) {
          const auto *object = llvm::dyn_cast<clang::TemplateParamObjectDecl>(
              argument.getAsDecl());
          if (object) {
            native_value = &object->getValue();
            native_type = object->getType();
          }
        }
        if (!native_value)
          continue;
        ctk::match::v1::MatchBinding binding;
        ctk::ast::v1::APValue constant;
        SerializationContext context{ast_context};
        context.projection = ProjectionPolicy::Shallow;
        helpers::write_apvalue(*native_value, constant, native_type, context);
        helpers::finish_binding(binding, context);
        EXPECT_TRUE(binding.is_complete());
        if (constant.has_structure()) {
          saw_array_record = true;
          EXPECT_EQ(constant.structure().field_values_size(), 0);
          EXPECT_TRUE(has_unrequested(binding, "field_values"));
        }
        if (constant.has_union_value()) {
          saw_union = true;
          EXPECT_FALSE(constant.union_value().has_active_field());
          EXPECT_FALSE(constant.union_value().has_value());
          EXPECT_TRUE(has_unrequested(binding, "active_field"));
          EXPECT_TRUE(has_unrequested(binding, "APUnionValue.value"));
        }
      }
    }
  }
  EXPECT_TRUE(saw_array_record);
  EXPECT_TRUE(saw_union);
}

TEST(CachedValues, ShallowLValueAPValuesOmitBaseAndPathChildren) {
  auto ast = clang::tooling::buildASTFromCodeWithArgs(
      "int target = 7; constexpr const int *pointer = &target;", {"-std=c++23"},
      "fixture.cc", "ctk-test");
  ASSERT_TRUE(ast);
  const clang::VarDecl *pointer = nullptr;
  for (const auto *decl :
       ast->getASTContext().getTranslationUnitDecl()->decls())
    if (const auto *variable = llvm::dyn_cast<clang::VarDecl>(decl);
        variable && variable->getName() == "pointer")
      pointer = variable;
  ASSERT_NE(pointer, nullptr);
  const auto *native_value = pointer->evaluateValue();
  ASSERT_NE(native_value, nullptr);

  ctk::match::v1::MatchBinding binding;
  ctk::ast::v1::APValue value;
  SerializationContext context{ast->getASTContext()};
  context.projection = ProjectionPolicy::Shallow;
  helpers::write_apvalue(*native_value, value, pointer->getType(), context);
  helpers::finish_binding(binding, context);
  ASSERT_TRUE(value.has_lvalue());
  EXPECT_TRUE(binding.is_complete());
  EXPECT_EQ(value.lvalue().path_size(), 0);
  EXPECT_FALSE(value.lvalue().has_base());
  EXPECT_TRUE(has_unrequested(binding, "APLValue.path"));
  EXPECT_TRUE(has_unrequested(binding, "APLValue.base"));
}

TEST(CachedValues, ShallowClassTemplateFactsPreservePrimaryAndSpecializations) {
  auto ast = clang::tooling::buildASTFromCodeWithArgs(
      "template<class T, int N = 3> struct Box {}; "
      "template<class T> struct Box<T*, 3> {}; "
      "template<> struct Box<double, 3> {}; Box<int, 3> object;",
      {"-std=c++20"}, "fixture.cc", "ctk-test");
  ASSERT_TRUE(ast);
  auto &ast_context = ast->getASTContext();
  const clang::ClassTemplateDecl *primary = nullptr;
  const clang::ClassTemplatePartialSpecializationDecl *partial = nullptr;
  for (const auto *decl : ast_context.getTranslationUnitDecl()->decls()) {
    if (const auto *value = llvm::dyn_cast<clang::ClassTemplateDecl>(decl))
      primary = value;
    if (const auto *value =
            llvm::dyn_cast<clang::ClassTemplatePartialSpecializationDecl>(decl))
      partial = value;
  }
  ASSERT_NE(primary, nullptr);
  ASSERT_NE(partial, nullptr);
  using Facts = ctk::match::v1::ClassTemplateFacts;
  auto serialize = [&](const clang::Decl &decl) {
    SerializationContext context{ast_context};
    context.projection = ProjectionPolicy::Shallow;
    ctk::match::v1::MatchBinding binding;
    EXPECT_TRUE(NodeSerializerDispatcher::serialize(
        clang::DynTypedNode::create(decl), binding, context));
    EXPECT_EQ(context.projection, ProjectionPolicy::Shallow);
    EXPECT_TRUE(binding.is_complete());
    return binding;
  };
  auto binding = serialize(*primary->getTemplatedDecl());
  ASSERT_TRUE(binding.has_class_template());
  EXPECT_EQ(binding.class_template().kind(), Facts::PRIMARY);
  ASSERT_EQ(binding.class_template().parameters_size(), 2);
  EXPECT_EQ(binding.class_template().parameters(0).name(), "T");
  EXPECT_EQ(binding.class_template().parameters(1).type().spelling(), "int");
  EXPECT_EQ(binding.class_template().primary_template().qualified_name(),
            "Box");
  auto wrapper = serialize(*primary);
  EXPECT_EQ(wrapper.class_template().parameters_size(), 2);
  EXPECT_TRUE(has_unrequested(wrapper, "parameters"));
  auto partial_binding = serialize(*partial);
  EXPECT_EQ(partial_binding.class_template().kind(),
            Facts::PARTIAL_SPECIALIZATION);
  EXPECT_EQ(partial_binding.class_template().parameters_size(), 1);
  EXPECT_EQ(partial_binding.class_template().arguments_size(), 2);
  EXPECT_TRUE(has_unrequested(partial_binding, "template_arguments"));
  int explicit_count = 0;
  int implicit_count = 0;
  for (const auto *specialization : primary->specializations()) {
    auto value = serialize(*specialization);
    const auto &facts = value.class_template();
    EXPECT_EQ(facts.kind(), Facts::SPECIALIZATION);
    ASSERT_EQ(facts.arguments_size(), 2);
    EXPECT_EQ(facts.arguments(1).semantic_spelling(), "3");
    EXPECT_EQ(value.node()
                  .class_template_specialization_decl()
                  .template_arguments_size(),
              0);
    EXPECT_TRUE(has_unrequested(value, "template_arguments"));
    if (facts.specialization_kind() ==
        ctk::ast::v1::
            DECL_TEMPLATE_SPECIALIZATION_KIND_EXPLICIT_SPECIALIZATION) {
      ++explicit_count;
      EXPECT_EQ(facts.display_name(), "Box<double, 3>");
    } else {
      ++implicit_count;
      EXPECT_EQ(facts.specialization_kind(),
                ctk::ast::v1::
                    DECL_TEMPLATE_SPECIALIZATION_KIND_IMPLICIT_INSTANTIATION);
      EXPECT_EQ(facts.display_name(), "Box<int, 3>");
    }
  }
  EXPECT_EQ(explicit_count, 1);
  EXPECT_EQ(implicit_count, 1);
}

TEST(CachedValues, ClassTemplateFactsDescribeNestedParametersAndPacks) {
  auto ast = clang::tooling::buildASTFromCodeWithArgs(
      "template<class... Ts> struct Pack {}; Pack<int, double> object; "
      "template<template<class...> class C> struct Wrapper {};",
      {"-std=c++20"}, "fixture.cc", "ctk-test");
  ASSERT_TRUE(ast);
  bool saw_pack = false;
  bool saw_nested = false;
  for (const auto *decl :
       ast->getASTContext().getTranslationUnitDecl()->decls()) {
    const auto *primary = llvm::dyn_cast<clang::ClassTemplateDecl>(decl);
    if (!primary)
      continue;
    SerializationContext context{ast->getASTContext()};
    context.projection = ProjectionPolicy::Shallow;
    ctk::match::v1::MatchBinding binding;
    helpers::write_class_template_facts(clang::DynTypedNode::create(*primary),
                                        binding, context);
    if (primary->getName() == "Wrapper") {
      ASSERT_EQ(binding.class_template().parameters_size(), 1);
      const auto &parameter = binding.class_template().parameters(0);
      ASSERT_EQ(parameter.template_parameters_size(), 1);
      EXPECT_TRUE(parameter.template_parameters(0).is_parameter_pack());
      saw_nested = true;
    }
    for (const auto *specialization : primary->specializations()) {
      SerializationContext specialized_context{ast->getASTContext()};
      specialized_context.projection = ProjectionPolicy::Shallow;
      ctk::match::v1::MatchBinding specialized;
      helpers::write_class_template_facts(
          clang::DynTypedNode::create(*specialization), specialized,
          specialized_context);
      ASSERT_EQ(specialized.class_template().arguments_size(), 1);
      const auto &pack = specialized.class_template().arguments(0);
      EXPECT_EQ(pack.kind(),
                ctk::ast::v1::TEMPLATE_ARGUMENT_DESCRIPTION_KIND_PACK);
      ASSERT_EQ(pack.pack_elements_size(), 2);
      EXPECT_EQ(pack.pack_elements(0).type().spelling(), "int");
      EXPECT_EQ(pack.pack_elements(1).type().spelling(), "double");
      EXPECT_TRUE(specialized_context.complete);
      EXPECT_EQ(specialized_context.projection, ProjectionPolicy::Shallow);
      saw_pack = true;
    }
  }
  EXPECT_TRUE(saw_pack);
  EXPECT_TRUE(saw_nested);
}

TEST(CachedValues, ClassTemplateFactsRespectDepthAndNodeBudgets) {
  auto ast = clang::tooling::buildASTFromCodeWithArgs(
      "template<class... Ts> struct Pack {}; Pack<int, double> object;",
      {"-std=c++20"}, "fixture.cc", "ctk-test");
  ASSERT_TRUE(ast);
  const clang::ClassTemplateDecl *primary = nullptr;
  for (const auto *decl :
       ast->getASTContext().getTranslationUnitDecl()->decls())
    if (const auto *value = llvm::dyn_cast<clang::ClassTemplateDecl>(decl))
      primary = value;
  ASSERT_NE(primary, nullptr);
  ASSERT_FALSE(primary->specializations().empty());
  const auto *specialization = *primary->specializations().begin();
  for (bool depth_limit : {false, true}) {
    SerializationContext context{ast->getASTContext()};
    context.projection = ProjectionPolicy::Shallow;
    if (depth_limit)
      context.max_depth = 1;
    else
      context.max_nodes = 1;
    ctk::match::v1::MatchBinding binding;
    helpers::write_class_template_facts(
        clang::DynTypedNode::create(*specialization), binding, context);
    helpers::finish_binding(binding, context);
    EXPECT_FALSE(binding.is_complete());
    EXPECT_EQ(context.projection, ProjectionPolicy::Shallow);
    EXPECT_LE(context.nodes, context.max_nodes);
    bool truncated = false;
    for (const auto &entry : binding.availability())
      truncated |= entry.state() == ctk::ast::v1::FIELD_STATE_TRUNCATED;
    EXPECT_TRUE(truncated);
    if (binding.class_template().arguments_size())
      EXPECT_EQ(binding.class_template().arguments(0).pack_elements_size(), 0);
  }
}
} // namespace
} // namespace ctk::clang_layer::serialization::testing
