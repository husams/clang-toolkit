#include "offset_of_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool OffsetOfExprSerializer::serialize(const clang::DynTypedNode &node,
                                       ctk::match::v1::MatchBinding &binding,
                                       SerializationContext &context) const {
  const auto *native = node.get<clang::OffsetOfExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_offset_of_expr();
  helpers::write_common(*native, *payload, context);
  helpers::write_type(native->getTypeSourceInfo()->getType(),
                      *payload->mutable_queried_type(), context);
  for (unsigned i = 0; i < native->getNumComponents(); ++i) {
    if (!helpers::can_expand(*payload, "components", context))
      break;

    const auto &native_component = native->getComponent(i);
    auto *component = payload->add_components();
    switch (native_component.getKind()) {
    case clang::OffsetOfNode::Field:
      helpers::write_symbol(*native_component.getField(),
                            *component->mutable_field(), context);
      break;
    case clang::OffsetOfNode::Identifier:
      component->set_identifier_name(
          native_component.getFieldName()->getName().str());
      break;
    case clang::OffsetOfNode::Base:
      helpers::write_base(*native_component.getBase(),
                          *component->mutable_base(), context);
      break;
    case clang::OffsetOfNode::Array: {
      const auto *index =
          native->getIndexExpr(native_component.getArrayExprIndex());
      helpers::write_expr(index, *component->mutable_index_expression(),
                          context);
      break;
    }
    }
  }
  if (!native->isValueDependent() &&
      helpers::can_expand(*payload, "byte_offset", context)) {
    clang::Expr::EvalResult evaluated;
    if (native->EvaluateAsInt(evaluated, context.ast_context))
      helpers::write_apint(evaluated.Val.getInt(),
                           *payload->mutable_byte_offset());
    else
      helpers::unavailable("byte_offset",
                           "Offset expression cannot be evaluated in this AST",
                           context);
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
