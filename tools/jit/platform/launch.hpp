#pragma once

#include <filesystem>

#include <llvm/ADT/StringRef.h>
#include <llvm/Support/Error.h>

namespace ctk::jit {

/// Replace the launcher process and preserve the terminal and exit status.
llvm::Error launch_cli(llvm::StringRef executable, char **argv);

std::filesystem::path state_root();
void configure_ast_cache();

} // namespace ctk::jit
