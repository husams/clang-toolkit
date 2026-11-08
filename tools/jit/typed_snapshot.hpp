#pragma once

#include "values.hpp"

#include <llvm/Support/Error.h>

namespace ctk::jit {

llvm::Expected<std::string> encode_snapshot(const Value& value);
llvm::Expected<Value> decode_snapshot(llvm::StringRef bytes);

} // namespace ctk::jit
