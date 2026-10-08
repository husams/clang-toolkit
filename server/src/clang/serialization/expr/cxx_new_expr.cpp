#include "cxx_new_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool CXXNewExprSerializer::serialize(const clang::DynTypedNode &node,
                                     ctk::match::v1::MatchBinding &binding,
                                     SerializationContext &context) const {
  const auto *native = node.get<clang::CXXNewExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_cxx_new_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getOperatorNew())
    helpers::write_symbol(*value, *payload->mutable_operator_new(), context);
  if (auto *value = native->getOperatorDelete())
    helpers::write_symbol(*value, *payload->mutable_operator_delete(), context);
  helpers::write_type(native->getAllocatedType(),
                      *payload->mutable_allocated_type(), context);
  if (auto size = native->getArraySize())
    helpers::write_expr(*size, *payload->mutable_array_size(), context);
  if (auto *value = native->getInitializer())
    helpers::write_expr(value, *payload->mutable_initializer(), context);
  payload->set_is_array(native->isArray());
  payload->set_is_global_new(native->isGlobalNew());
  payload->set_is_placement(native->getNumPlacementArgs() != 0);
  if (auto *function = native->getOperatorNew()) {
    if (const auto *type =
            function->getType()->getAs<clang::FunctionProtoType>())
      payload->set_is_nothrow(type->isNothrow());
  }
  for (unsigned i = 0; i < native->getNumPlacementArgs(); ++i) {
    if (!helpers::can_expand(*payload, "placement_arguments", context))
      break;
    helpers::write_expr(native->getPlacementArg(i),
                        *payload->add_placement_arguments(), context);
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
