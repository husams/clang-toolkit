#include "compilation_environment.hpp"
#include <cstdlib>
namespace ctk::clang_layer::snapshot {
std::vector<std::pair<std::string, std::string>> compilation_environment() {
  std::vector<std::pair<std::string, std::string>> values;
  // Driver include/config/SDK/module selection and reproducible builtin dates.
  // Store only compiler inputs, never the unrestricted process environment.
  for (const auto *name : {"CPATH",
                           "CPLUS_INCLUDE_PATH",
                           "C_INCLUDE_PATH",
                           "OBJC_INCLUDE_PATH",
                           "SDKROOT",
                           "MACOSX_DEPLOYMENT_TARGET",
                           "CLANG_MODULE_CACHE_PATH",
                           "SOURCE_DATE_EPOCH",
                           "CCC_OVERRIDE_OPTIONS",
                           "CLANG_CONFIG_PATH",
                           "CLANG_NO_DEFAULT_CONFIG",
                           "COMPILER_PATH",
                           "CLANG_TOOLCHAIN_PROGRAM_TIMEOUT",
                           "IPHONEOS_DEPLOYMENT_TARGET",
                           "TVOS_DEPLOYMENT_TARGET",
                           "WATCHOS_DEPLOYMENT_TARGET",
                           "DRIVERKIT_DEPLOYMENT_TARGET",
                           "XROS_DEPLOYMENT_TARGET",
                           "LIBCLANG_DISABLE_PCH_VALIDATION",
                           "INCLUDE",
                           "LIBRARY_PATH",
                           "HOME",
                           "XDG_CONFIG_HOME",
                           "TMPDIR",
                           "TEMP",
                           "TMP"})
    if (const auto *value = std::getenv(name))
      values.emplace_back(name, value);
  return values;
}
} // namespace ctk::clang_layer::snapshot
