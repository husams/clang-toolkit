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
      "int target = 7; constexpr const int *pointer = &target;",
      {"-std=c++23"}, "fixture.cc", "ctk-test");
  ASSERT_TRUE(ast);
  const clang::VarDecl *pointer = nullptr;
  for (const auto *decl : ast->getASTContext().getTranslationUnitDecl()->decls())
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
} // namespace
} // namespace ctk::clang_layer::serialization::testing
