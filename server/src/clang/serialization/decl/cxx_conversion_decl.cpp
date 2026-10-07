#include "cxx_conversion_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool CXXConversionDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::CXXConversionDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_cxx_conversion_decl();
  helpers::write_common(*native, *payload, context);
  const auto explicit_specifier = native->getExplicitSpecifier();
  payload->set_is_explicit(native->isExplicit());
  if (explicit_specifier.getKind() != clang::ExplicitSpecKind::Unresolved)
    payload->set_is_explicit_specifier_value(explicit_specifier.isExplicit());
  if (explicit_specifier.getExpr())
    helpers::write_expr(explicit_specifier.getExpr(),
                        *payload->mutable_explicit_specifier_expression(),
                        context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
