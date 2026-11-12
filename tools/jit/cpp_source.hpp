#pragma once

#include <string>
#include <llvm/ADT/StringRef.h>
#include <llvm/Support/Error.h>

namespace ctk::jit {

llvm::Expected<std::string> cpp_source(llvm::StringRef source,
                                      llvm::StringRef path, bool ctk);

} // namespace ctk::jit
