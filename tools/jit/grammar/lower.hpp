#pragma once

#include <string>

#include <llvm/ADT/StringRef.h>
#include <llvm/Support/Error.h>

namespace ctk::jit {

/// Compile a CTK source submission to the runner's LLVM IR entry ABI.
llvm::Expected<std::string> lower_ctk(llvm::StringRef source,
                                      bool display = true,
                                      llvm::StringRef path = {},
                                      bool library = false,
                                      bool *incomplete = nullptr);

} // namespace ctk::jit
