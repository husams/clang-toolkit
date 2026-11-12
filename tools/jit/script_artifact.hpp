#pragma once

#include <filesystem>
#include <memory>
#include <vector>

#include <llvm/ADT/StringRef.h>
#include <llvm/Support/Error.h>
#include <llvm/Support/MemoryBuffer.h>

namespace ctk::jit {

struct ScriptToolchain {
  llvm::StringRef compiler;
  std::vector<const char *> flags;
  std::filesystem::path executable;
  std::filesystem::path runtime_header;
  std::vector<std::filesystem::path> dependencies;
};

struct ScriptProgram {
  std::unique_ptr<llvm::MemoryBuffer> input;
  std::string quote_directory;
  bool llvm_ir;
  bool object;
};

llvm::Expected<ScriptProgram> script_program(const std::filesystem::path &script,
                                            bool llvm_ir, bool no_cache,
                                            const ScriptToolchain &toolchain);
llvm::Error precompile_script(const std::filesystem::path &script,
                              const std::filesystem::path &output, bool llvm_ir,
                              bool no_cache, const ScriptToolchain &toolchain);
llvm::Expected<ScriptProgram> read_script_bundle(
    const std::filesystem::path &path, const ScriptToolchain &toolchain);

} // namespace ctk::jit
