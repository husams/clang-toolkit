#pragma once
#include "analysis/v1/cfg_options.pb.h"
#include <clang/Analysis/CFG.h>
namespace ctk::clang_layer::control_flow {
clang::CFG::BuildOptions build_options(const ctk::analysis::v1::CfgOptions &);
}
