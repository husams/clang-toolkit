#pragma once
#include "analysis/v1/script_value.pb.h"
#include "ctk/clang/matching.hpp"
namespace ctk::script {
// Published values are immutable and cheap to alias across lexical scopes.
struct Value {
  std::shared_ptr<const ctk::analysis::v1::ScriptValue> wire;
  std::shared_ptr<const ctk::clang_layer::NativeBindingState> bindings;
  std::shared_ptr<const std::vector<std::size_t>> native_rows;
};
} // namespace ctk::script
