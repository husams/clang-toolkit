#pragma once

#include <string>
#include <vector>

namespace ctk::clang_layer {

inline std::vector<std::string> configured_driver_defaults() {
  std::vector<std::string> arguments{"-resource-dir=" CTK_CLANG_RESOURCE_DIR};
#ifdef CTK_ANALYSIS_SYSROOT
  arguments.emplace_back("--sysroot=" CTK_ANALYSIS_SYSROOT);
#endif
#ifdef CTK_ANALYSIS_GCC_TOOLCHAIN
  arguments.emplace_back("--gcc-toolchain=" CTK_ANALYSIS_GCC_TOOLCHAIN);
#endif
  return arguments;
}

} // namespace ctk::clang_layer
