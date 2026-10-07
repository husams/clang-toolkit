#pragma once
#include "../cfg_element_dispatcher.hpp"
namespace ctk::clang_layer::control_flow {
class CFGLoopExitSerializer final {
public:
  void serialize(const clang::CFGElement &, ctk::analysis::v1::CfgElement &,
                 Context &) const;
};
} // namespace ctk::clang_layer::control_flow
