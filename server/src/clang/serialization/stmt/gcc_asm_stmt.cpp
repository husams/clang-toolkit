#include "gcc_asm_stmt.hpp"
#include "../semantic_helpers.hpp"
#include <clang/AST/Attr.h>
#include <clang/AST/ParentMapContext.h>
namespace ctk::clang_layer::serialization {
bool GCCAsmStmtSerializer::serialize(const clang::DynTypedNode &node,
                                     ctk::match::v1::MatchBinding &binding,
                                     SerializationContext &context) const {
  const auto *native = node.get<clang::GCCAsmStmt>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_gcc_asm_stmt();
  payload->set_asm_string(native->getAsmString());
  payload->set_is_simple(native->isSimple());
  payload->set_is_volatile(native->isVolatile());
  payload->set_is_goto(native->isAsmGoto());
  payload->set_dialect("gnu");
  for (unsigned i = 0; i < native->getNumOutputs(); ++i) {
    if (!helpers::can_expand("gcc_asm_stmt.outputs", context))
      break;
    auto *operand = payload->add_outputs();
    operand->set_constraint(native->getOutputConstraint(i));
    if (!native->getOutputName(i).empty())
      operand->set_symbolic_name(native->getOutputName(i).str());
    if (auto *expr = native->getOutputExpr(i))
      helpers::write_expr(expr, *operand->mutable_expression(), context);
  }
  for (unsigned i = 0; i < native->getNumInputs(); ++i) {
    if (!helpers::can_expand("gcc_asm_stmt.inputs", context))
      break;
    auto *operand = payload->add_inputs();
    operand->set_constraint(native->getInputConstraint(i));
    if (!native->getInputName(i).empty())
      operand->set_symbolic_name(native->getInputName(i).str());
    if (auto *expr = native->getInputExpr(i))
      helpers::write_expr(expr, *operand->mutable_expression(), context);
  }
  for (unsigned i = 0; i < native->getNumClobbers(); ++i)
    payload->add_clobbers(native->getClobber(i));
  for (unsigned i = 0; i < native->getNumLabels(); ++i) {
    if (!helpers::can_expand("GCCAsmStmt.goto_labels", context))
      break;
    helpers::write_symbol(*native->getLabelExpr(i)->getLabel(),
                          *payload->add_goto_labels(), context);
  }
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
