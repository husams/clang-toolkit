#pragma once
#include "ctk/clang/matching.hpp"
namespace ctk::clang_layer {
MatchExecution navigate_bindings(
    const ctk::match::v1::MatchRequest &,
    std::shared_ptr<const NativeBindingState>,
    const IMatchBackend::Checkpoint &, const MatchLimits &,
    const IMatchBackend::RowSink *, bool retain_target = true);
}
