#pragma once

#include <filesystem>
#include <string>

#include <llvm/ADT/ArrayRef.h>
#include <llvm/ADT/StringRef.h>
#include <llvm/Support/Error.h>

namespace ctk::jit {

/// Replace the launcher process and preserve the terminal and exit status.
llvm::Error launch_cli(llvm::StringRef executable, char **argv);

std::filesystem::path state_root();
void configure_ast_cache();
bool prepare_private_cache(const std::filesystem::path &path);
llvm::Error write_atomic(const std::filesystem::path &path, llvm::StringRef data);
bool apple_driver_needs_sdk(llvm::ArrayRef<std::string> command,
                            llvm::StringRef directory);
bool is_gcc_driver(const std::filesystem::path &driver);

} // namespace ctk::jit
