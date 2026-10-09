#include "cfg_block.hpp"
#include "cfg_edge.hpp"
namespace ctk::clang_layer::control_flow {
void write_block(const clang::CFGBlock &native,
                 ctk::analysis::v1::CfgBlock &output, Context &context,
                 CfgBudget &budget) {
  namespace helpers = serialization::helpers;
  budget.check();
  if (++budget.blocks > budget.limits.max_blocks)
    throw BuildFailure(MatchCode::ResourceExhausted,
                       "CFG block limit exceeded");
  output.set_block_index(native.getBlockID());
  for (const auto &element : native) {
    budget.check();
    if (++budget.elements > budget.limits.max_elements)
      throw BuildFailure(MatchCode::ResourceExhausted,
                         "CFG element limit exceeded");
    auto child = fresh_context(context);
    auto *value = output.add_elements();
    CfgElementDispatcher::serialize(element, *value, child);
    context.complete &= child.complete;
    context.availability.insert(context.availability.end(),
                                child.availability.begin(),
                                child.availability.end());
    budget.add_bytes(value->ByteSizeLong());
  }
  for (const auto &edge : native.preds())
    write_edge(edge, *output.add_predecessors());
  for (const auto &edge : native.succs())
    write_edge(edge, *output.add_successors());
  if (auto *value = native.getLabel())
    helpers::write_stmt(value, *output.mutable_label(), context);
  if (auto *value = native.getLoopTarget())
    helpers::write_stmt(value, *output.mutable_loop_target(), context);
  const auto terminator = native.getTerminator();
  if (terminator.isValid()) {
    switch (terminator.getKind()) {
    case clang::CFGTerminator::StmtBranch:
      output.set_terminator_kind(ctk::analysis::v1::CfgBlock::STATEMENT_BRANCH);
      break;
    case clang::CFGTerminator::TemporaryDtorsBranch:
      output.set_terminator_kind(
          ctk::analysis::v1::CfgBlock::TEMPORARY_DTORS_BRANCH);
      break;
    case clang::CFGTerminator::VirtualBaseBranch:
      output.set_terminator_kind(
          ctk::analysis::v1::CfgBlock::VIRTUAL_BASE_BRANCH);
      break;
    }
    if (auto *value = terminator.getStmt())
      helpers::write_stmt(value, *output.mutable_terminator(), context);
  }
  if (auto *value = native.getTerminatorCondition())
    helpers::write_stmt(value, *output.mutable_terminator_condition(), context);
  if (auto *value = native.getLastCondition())
    helpers::write_expr(value, *output.mutable_last_condition(), context);
  output.set_has_no_return_element(native.hasNoReturnElement());
  finish(output, context);
  // Include metadata and repeated-field framing in the publication check.
  std::size_t element_bytes = 0;
  for (const auto &element : output.elements())
    element_bytes += element.ByteSizeLong();
  budget.add_bytes(output.ByteSizeLong() - element_bytes);
}
} // namespace ctk::clang_layer::control_flow
