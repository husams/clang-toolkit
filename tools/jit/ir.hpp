#pragma once

#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <utility>
#include <vector>

#include <llvm/ADT/StringRef.h>
#include <llvm/Support/Error.h>
#include <llvm/Support/MemoryBuffer.h>

namespace clang {
class ASTContext;
class ASTUnit;
} // namespace clang

namespace ctk::jit {

struct TargetRequest {
  std::string file;
  std::string directory;
  std::string compilation_database;
  std::vector<std::string> arguments;
  std::optional<std::string> source;
};

using LoadTarget =
    std::function<llvm::Expected<std::unique_ptr<clang::ASTUnit>>(const TargetRequest&)>;

using ScriptArguments = std::vector<std::pair<std::string, std::string>>;

llvm::Error compile_ir(llvm::StringRef source);
llvm::Error run_ir(std::unique_ptr<llvm::MemoryBuffer> input, std::unique_ptr<clang::ASTUnit> ast,
                   bool precompiled, llvm::StringRef file, llvm::StringRef database,
                   const LoadTarget& load, const ScriptArguments& arguments);
llvm::Error repl_ir(std::unique_ptr<clang::ASTUnit> ast, llvm::StringRef file, llvm::StringRef database,
                    const LoadTarget& load, const ScriptArguments& arguments);

} // namespace ctk::jit
