#pragma once
#include "analysis/v1/cfg_graph.pb.h"
#include "cfg_block.hpp"
namespace ctk::clang_layer::control_flow {
void write_graph(const clang::FunctionDecl &, const clang::CFG &,
                 ctk::analysis::v1::CfgGraph &, Context &, CfgBudget &);
}
