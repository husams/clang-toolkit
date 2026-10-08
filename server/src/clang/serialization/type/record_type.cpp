#include "record_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool RecordTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::RecordType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_record_type();
  helpers::write_common(*native, *payload, context);
  helpers::write_symbol(*native->getDecl(), *payload->mutable_declaration(), context);
#if CLANG_VERSION_MAJOR >= 22
  helpers::write_nested_name(native->getQualifier(), *payload->mutable_qualifier(), context);
#else
  helpers::unavailable(*payload, "qualifier", "this Clang version does not retain a qualifier on this type node", context);
#endif
  if (auto *record = llvm::dyn_cast<clang::CXXRecordDecl>(native->getDecl())) {
    if (auto *specialization = llvm::dyn_cast<clang::ClassTemplateSpecializationDecl>(record)) {
      auto *templ = specialization->getSpecializedTemplate();
      helpers::write_symbol(*templ, *payload->mutable_template_declaration(), context);
      helpers::write_template_name(clang::TemplateName(templ), *payload->mutable_template_name(), context);
      for (const auto &argument : specialization->getTemplateArgs().asArray()) {
        if (!helpers::can_expand(*payload, "specialization_arguments", context)) break;
        helpers::write_template_argument(argument, *payload->add_specialization_arguments(), context);
      }
    } else if (auto *templ = record->getDescribedClassTemplate()) {
      helpers::write_symbol(*templ, *payload->mutable_template_declaration(), context);
      helpers::write_template_name(clang::TemplateName(templ), *payload->mutable_template_name(), context);
    }
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
