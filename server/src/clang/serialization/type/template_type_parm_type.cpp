#include "template_type_parm_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool TemplateTypeParmTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::TemplateTypeParmType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_template_type_parm_type();
  helpers::write_common(*native, *payload, context);
  payload->set_depth(native->getDepth());
  payload->set_index(native->getIndex());
  payload->set_is_pack(native->isParameterPack());
  if (native->getDecl()) helpers::write_symbol(*native->getDecl(), *payload->mutable_declaration(), context);
  if (native->getIdentifier()) payload->set_identifier(native->getIdentifier()->getName().str());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
