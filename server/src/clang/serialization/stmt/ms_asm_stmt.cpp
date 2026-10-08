#include "ms_asm_stmt.hpp"
#include "../semantic_helpers.hpp"
#include <clang/AST/Attr.h>
#include <clang/AST/ParentMapContext.h>
namespace ctk::clang_layer::serialization {
bool MSAsmStmtSerializer::serialize(const clang::DynTypedNode &node,
                                    ctk::match::v1::MatchBinding &binding,
                                    SerializationContext &context) const {
  const auto *native = node.get<clang::MSAsmStmt>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_ms_asm_stmt();
  payload->set_asm_string(native->getAsmString().str());
  payload->set_is_simple(native->isSimple());
  payload->set_is_volatile(native->isVolatile());
  payload->set_is_goto(false);
  payload->set_dialect("ms");
  for (unsigned i = 0; i < native->getNumOutputs(); ++i) {
    if (!helpers::can_expand(*payload, "outputs", context))
      break;
    auto *operand = payload->add_outputs();
    operand->set_constraint(native->getOutputConstraint(i).str());

    if (auto *expr = native->getOutputExpr(i))
      helpers::write_expr(expr, *operand->mutable_expression(), context);
  }
  for (unsigned i = 0; i < native->getNumInputs(); ++i) {
    if (!helpers::can_expand(*payload, "inputs", context))
      break;
    auto *operand = payload->add_inputs();
    operand->set_constraint(native->getInputConstraint(i).str());

    if (auto *expr = native->getInputExpr(i))
      helpers::write_expr(expr, *operand->mutable_expression(), context);
  }
  for (unsigned i = 0; i < native->getNumClobbers(); ++i)
    payload->add_clobbers(native->getClobber(i).str());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
