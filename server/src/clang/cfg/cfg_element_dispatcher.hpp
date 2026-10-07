#pragma once
#include "analysis/v1/cfg_element.pb.h"
#include "cfg_value_helpers.hpp"
#include <clang/Analysis/CFG.h>

namespace ctk::clang_layer::control_flow {
class CfgElementDispatcher final {
public:
  static void serialize(const clang::CFGElement &,
                        ctk::analysis::v1::CfgElement &, Context &);
};
} // namespace ctk::clang_layer::control_flow
