#pragma once

#include "values.hpp"

namespace ctk::jit {

const Value* read_settings_file(Values& runtime, llvm::StringRef path);
bool write_settings_file(Values& runtime, llvm::StringRef path, const Value& value);
bool emit_text(Values& runtime, llvm::StringRef text);
llvm::Error expose_documents(llvm::orc::LLJIT& jit);

} // namespace ctk::jit
