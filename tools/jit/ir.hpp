#pragma once

#include <functional>
#include <memory>
#include <optional>
#include <string>
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

llvm::Error compile_ir(llvm::StringRef source);
llvm::Error run_ir(std::unique_ptr<llvm::MemoryBuffer> input, clang::ASTContext& ast,
                   bool precompiled, llvm::StringRef file, const LoadTarget& load);
llvm::Error repl_ir(clang::ASTContext& ast, llvm::StringRef file, const LoadTarget& load);

} // namespace ctk::jit
