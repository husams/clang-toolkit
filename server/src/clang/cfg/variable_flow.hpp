#pragma once
#include "ctk/clang/cfg_backend.hpp"
namespace ctk::clang_layer::control_flow {
CfgResult variable_flow(const ctk::analysis::v1::VariableFlowRequest &,
                        std::shared_ptr<const NativeBindingState>,
                        std::shared_ptr<const NativeBindingState>,
                        const IMatchBackend::Checkpoint &, const CfgLimits &,
                        const ICfgBackend::VariableSink &);
}
