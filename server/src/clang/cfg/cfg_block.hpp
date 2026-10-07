#pragma once
#include "analysis/v1/cfg_block.pb.h"
#include "cfg_budget.hpp"
#include "cfg_element_dispatcher.hpp"
namespace ctk::clang_layer::control_flow {
void write_block(const clang::CFGBlock &, ctk::analysis::v1::CfgBlock &,
                 Context &, CfgBudget &);
}
