#pragma once

#include <llvm/ADT/StringRef.h>
#include <llvm/Support/Error.h>

namespace ctk::jit {

/// Replace the launcher process and preserve the terminal and exit status.
llvm::Error launch_cli(llvm::StringRef executable, char **argv);

} // namespace ctk::jit
