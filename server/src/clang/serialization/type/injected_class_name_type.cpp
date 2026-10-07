#include "injected_class_name_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool InjectedClassNameTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::InjectedClassNameType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_injected_class_name_type();
  helpers::write_common(*native, *payload, context);
  helpers::write_symbol(*native->getDecl(), *payload->mutable_declaration(), context);
#if CLANG_VERSION_MAJOR >= 22
  helpers::write_nested_name(native->getQualifier(), *payload->mutable_qualifier(), context);
#else
  helpers::unavailable(*payload, "qualifier", "this Clang version does not retain a qualifier on this type node", context);
#endif
  if (auto *templ = native->getDecl()->getDescribedClassTemplate()) {
    helpers::write_symbol(*templ, *payload->mutable_template_declaration(), context);
    helpers::write_template_name(clang::TemplateName(templ), *payload->mutable_template_name(), context);
    for (const auto &argument : templ->getInjectedTemplateArgs(context.ast_context)) {
      if (!helpers::can_expand("specialization_arguments", context)) break;
      helpers::write_template_argument(argument, *payload->add_specialization_arguments(), context);
    }
  }
  if (const auto *specialization = llvm::dyn_cast<clang::ClassTemplatePartialSpecializationDecl>(native->getDecl())) {
    auto *templ = specialization->getSpecializedTemplate();
    helpers::write_symbol(*templ, *payload->mutable_template_declaration(), context);
    helpers::write_template_name(clang::TemplateName(templ), *payload->mutable_template_name(), context);
    for (const auto &argument : specialization->getTemplateArgs().asArray()) {
      if (!helpers::can_expand("specialization_arguments", context)) break;
      helpers::write_template_argument(argument, *payload->add_specialization_arguments(), context);
    }
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
