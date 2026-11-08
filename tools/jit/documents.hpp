#pragma once

#include "values.hpp"

namespace ctk::jit {

bool emit_text(Values& runtime, llvm::StringRef text);
llvm::Error expose_documents(llvm::orc::LLJIT& jit);

} // namespace ctk::jit
