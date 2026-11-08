#pragma once

#include "values.hpp"

namespace ctk::jit {

bool load_settings(Values& runtime);
const Value* update_setting(Values& runtime, llvm::StringRef name, const Value* value, bool user,
                            bool append);

} // namespace ctk::jit
