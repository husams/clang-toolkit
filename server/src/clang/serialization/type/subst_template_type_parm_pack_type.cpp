#include "subst_template_type_parm_pack_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool SubstTemplateTypeParmPackTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::SubstTemplateTypeParmPackType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_subst_template_type_parm_pack_type();
  helpers::write_common(*native, *payload, context);
  if (auto *associated = llvm::dyn_cast<clang::NamedDecl>(native->getAssociatedDecl()))
    helpers::write_symbol(*associated, *payload->mutable_associated_declaration(), context);
  else if (native->getAssociatedDecl()) helpers::unavailable(*payload, "associated_declaration", "associated native declaration has no name/symbol contract", context);
  if (auto *replaced = native->getReplacedParameter())
    helpers::write_symbol(*replaced, *payload->mutable_replaced_parameter(), context);
  payload->set_parameter_index(native->getIndex());
  payload->set_is_final(native->getFinal());
  helpers::write_template_argument(native->getArgumentPack(), *payload->mutable_argument_pack(), context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
