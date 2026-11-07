#pragma once

#include <memory>

#include <llvm/ADT/StringRef.h>
#include <llvm/Support/Error.h>
#include <llvm/Support/MemoryBuffer.h>

namespace clang {
class ASTContext;
}

namespace ctk::jit {

llvm::Error compile_ir(llvm::StringRef source);
llvm::Error run_ir(std::unique_ptr<llvm::MemoryBuffer> input, clang::ASTContext& ast,
                   bool precompiled);
llvm::Error repl_ir(clang::ASTContext& ast);

} // namespace ctk::jit
