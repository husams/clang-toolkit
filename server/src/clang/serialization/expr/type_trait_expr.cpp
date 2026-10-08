#include "type_trait_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool TypeTraitExprSerializer::serialize(const clang::DynTypedNode &node,
                                        ctk::match::v1::MatchBinding &binding,
                                        SerializationContext &context) const {
  const auto *native = node.get<clang::TypeTraitExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_type_trait_expr();
  helpers::write_common(*native, *payload, context);
  payload->set_trait(ctk::ast::v1::TYPE_TRAIT_OTHER);
  payload->set_trait_name(clang::getTraitName(native->getTrait()));
  for (unsigned i = 0; i < native->getNumArgs(); ++i) {
    if (!helpers::can_expand(*payload, "queried_types", context))
      break;
    helpers::write_type(native->getArg(i)->getType(),
                        *payload->add_queried_types(), context);
  }
  if (!native->isValueDependent()) {
#if CLANG_VERSION_MAJOR >= 21
    if (native->isStoredAsBoolean())
      payload->set_trait_value(native->getBoolValue());
    else
      helpers::write_apvalue(native->getAPValue(),
                             *payload->mutable_result_value(),
                             native->getType(), context);
#else
    payload->set_trait_value(native->getValue());
#endif
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
