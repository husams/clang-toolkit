#include "cfg_edge.hpp"
namespace ctk::clang_layer::control_flow {
void write_edge(const clang::CFGBlock::AdjacentBlock &native,
                ctk::analysis::v1::CfgEdge &output) {
  if (const auto *block = native.getReachableBlock())
    output.set_reachable_block(block->getBlockID());
  if (const auto *block = native.getPossiblyUnreachableBlock())
    output.set_possibly_unreachable_block(block->getBlockID());
  output.set_is_reachable(native.isReachable());
}
} // namespace ctk::clang_layer::control_flow
