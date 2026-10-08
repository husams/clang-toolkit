#include "atomic_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool AtomicExprSerializer::serialize(const clang::DynTypedNode &node,
                                     ctk::match::v1::MatchBinding &binding,
                                     SerializationContext &context) const {
  const auto *native = node.get<clang::AtomicExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_atomic_expr();
  helpers::write_common(*native, *payload, context);
  payload->set_opcode(helpers::atomic_opcode(native->getOp()));
  if (auto *name = helpers::atomic_name(native->getOp()))
    payload->set_opcode_name(name);
  else
    helpers::unavailable("opcode_name", "Unrecognized native atomic builtin",
                         context);
  for (unsigned i = 0; i < native->getNumSubExprs(); ++i) {
    if (!helpers::can_expand(*payload, "arguments", context))
      break;
    helpers::write_expr(native->getSubExprs()[i], *payload->add_arguments(),
                        context);
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
