#include "cfg_graph.hpp"
#include <algorithm>
namespace ctk::clang_layer::control_flow {
void write_graph(const clang::FunctionDecl &function, const clang::CFG &native,
                 ctk::analysis::v1::CfgGraph &output, Context &context,
                 CfgBudget &budget) {
  serialization::helpers::write_symbol(function, *output.mutable_function(),
                                       context);
  output.set_entry_block(native.getEntry().getBlockID());
  output.set_exit_block(native.getExit().getBlockID());
  output.set_is_linear(native.isLinear());
  std::vector<const clang::CFGBlock *> ordered(native.begin(), native.end());
  std::sort(ordered.begin(), ordered.end(),
            [](auto *a, auto *b) { return a->getBlockID() < b->getBlockID(); });
  for (auto *block : ordered) {
    auto child = fresh_context(context);
    write_block(*block, *output.add_blocks(), child, budget);
    context.complete &= child.complete;
    context.availability.insert(context.availability.end(),
                                child.availability.begin(),
                                child.availability.end());
  }
  finish(output, context);
  std::size_t block_bytes = 0;
  for (const auto &block : output.blocks())
    block_bytes += block.ByteSizeLong();
  budget.add_bytes(output.ByteSizeLong() - block_bytes);
}
} // namespace ctk::clang_layer::control_flow
