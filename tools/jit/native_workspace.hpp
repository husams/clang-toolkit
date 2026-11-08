#pragma once

#include "ir.hpp"

namespace ctk::jit {

llvm::Error run_native_workspace(llvm::StringRef file, llvm::StringRef database,
                                 const LoadTarget &load,
                                 const ScriptArguments &arguments);

} // namespace ctk::jit
