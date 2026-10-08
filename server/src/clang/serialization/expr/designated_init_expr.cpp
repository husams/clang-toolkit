#include "designated_init_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool DesignatedInitExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::DesignatedInitExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_designated_init_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getInit())
    helpers::write_expr(value, *payload->mutable_initializer(), context);
  for (const auto &designator : native->designators()) {
    if (!helpers::can_expand(*payload, "designators", context))
      break;

    auto *target = payload->add_designators();
    if (designator.isFieldDesignator()) {
      if (auto *field = designator.getFieldDecl())
        helpers::write_symbol(*field, *target->mutable_field_declaration(),
                              context);
      else
        helpers::unavailable("designators.field_declaration",
                             "Dependent field designator is unresolved",
                             context);
    } else if (designator.isArrayDesignator()) {
      helpers::write_expr(native->getArrayIndex(designator),
                          *target->mutable_array_index(), context);
    } else {
      helpers::write_expr(native->getArrayRangeStart(designator),
                          *target->mutable_array_range_start(), context);
      helpers::write_expr(native->getArrayRangeEnd(designator),
                          *target->mutable_array_range_end(), context);
    }
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
