#pragma once
#include "analysis/v1/cfg_edge.pb.h"
#include <clang/Analysis/CFG.h>
namespace ctk::clang_layer::control_flow {
void write_edge(const clang::CFGBlock::AdjacentBlock &,
                ctk::analysis::v1::CfgEdge &);
}
