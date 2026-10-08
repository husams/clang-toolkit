#include "cxx_constructor_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool CXXConstructorDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::CXXConstructorDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_cxx_constructor_decl();
  helpers::write_common(*native, *payload, context);
  for (const auto *initializer : native->inits()) {
    if (!helpers::can_expand(*payload, "initializers", context))
      break;

    auto *value = payload->add_initializers();
    if (initializer->isBaseInitializer())
      helpers::write_type(clang::QualType(initializer->getBaseClass(), 0),
                          *value->mutable_base_type(), context);
    else if (initializer->isMemberInitializer())
      helpers::write_symbol(*initializer->getMember(), *value->mutable_member(),
                            context);
    else if (initializer->isIndirectMemberInitializer())
      helpers::write_symbol(*initializer->getIndirectMember(),
                            *value->mutable_indirect_member(), context);
    else if (initializer->isDelegatingInitializer())
      helpers::write_type(initializer->getTypeSourceInfo()->getType(),
                          *value->mutable_delegating_type(), context);
    if (initializer->getInit())
      helpers::write_expr(initializer->getInit(), *value->mutable_initializer(),
                          context);
    value->set_is_virtual_base(initializer->isBaseInitializer() &&
                               initializer->isBaseVirtual());
    value->set_is_pack_expansion(initializer->isPackExpansion());
  }
  const auto explicit_specifier = native->getExplicitSpecifier();
  payload->set_is_explicit(native->isExplicit());
  if (explicit_specifier.getKind() != clang::ExplicitSpecKind::Unresolved)
    payload->set_is_explicit_specifier_value(explicit_specifier.isExplicit());
  if (explicit_specifier.getExpr())
    helpers::write_expr(explicit_specifier.getExpr(),
                        *payload->mutable_explicit_specifier_expression(),
                        context);
  payload->set_is_converting_constructor(
      native->isConvertingConstructor(false));
  payload->set_is_copy_constructor(native->isCopyConstructor());
  payload->set_is_move_constructor(native->isMoveConstructor());
  payload->set_is_default_constructor(native->isDefaultConstructor());
  payload->set_is_delegating_constructor(native->isDelegatingConstructor());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
