#pragma once

#include "values.hpp"

#include <llvm/ADT/ArrayRef.h>

namespace ctk::jit {

std::string format_float(double value);
bool is_builtin(llvm::StringRef name);
const Value* call_builtin(Values& runtime, llvm::StringRef name, llvm::ArrayRef<Value> args,
                          const Record& keywords);

// Functions in this section are also callable from generated IR.
extern "C" const Value* ctk_jit_value_invoke_v1(Values* runtime, const Value* value,
                                                const Value* arguments, const Value* keywords);
extern "C" const Value* ctk_jit_value_render_v1(Values* runtime, const Value* value);

} // namespace ctk::jit
