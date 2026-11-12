#pragma once

#include <filesystem>

#include "values.hpp"

namespace ctk::jit {

bool load_settings(Values& runtime);
std::filesystem::path configured_script_cache();
const Value* update_setting(Values& runtime, llvm::StringRef name, const Value* value, bool user,
                            bool append);

} // namespace ctk::jit
