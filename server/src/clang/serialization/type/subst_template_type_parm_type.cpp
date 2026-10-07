#include "subst_template_type_parm_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool SubstTemplateTypeParmTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::SubstTemplateTypeParmType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_subst_template_type_parm_type();
  helpers::write_common(*native, *payload, context);
  helpers::write_type(native->getReplacementType(), *payload->mutable_replacement_type(), context);
  if (auto *associated = llvm::dyn_cast<clang::NamedDecl>(native->getAssociatedDecl()))
    helpers::write_symbol(*associated, *payload->mutable_associated_declaration(), context);
  else if (native->getAssociatedDecl()) helpers::unavailable(*payload, "associated_declaration", "associated native declaration has no name/symbol contract", context);
  if (auto *replaced = native->getReplacedParameter())
    helpers::write_symbol(*replaced, *payload->mutable_replaced_parameter(), context);
  payload->set_parameter_index(native->getIndex());
  if (auto index = native->getPackIndex()) payload->set_pack_index(*index);
  payload->set_is_final(native->getFinal());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
