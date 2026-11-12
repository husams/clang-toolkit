#pragma once

#include "ir.hpp"

namespace ctk::jit {

llvm::Error run_native_prompt(llvm::StringRef file, llvm::StringRef database,
                              const LoadTarget &load,
                              const ScriptArguments &arguments, bool &failed);

} // namespace ctk::jit
