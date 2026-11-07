#pragma once

#include <llvm/ADT/StringRef.h>
#include <llvm/Support/Error.h>

namespace clang {
class ASTContext;
}

namespace ctk::jit {

llvm::Error run_ir(llvm::StringRef source, clang::ASTContext& ast);

} // namespace ctk::jit
