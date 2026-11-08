#include "launch.hpp"

#include <cerrno>
#include <unistd.h>

namespace ctk::jit {

llvm::Error launch_cli(llvm::StringRef executable, char **argv) {
  const auto path = executable.str();
  ::execv(path.c_str(), argv);
  return llvm::createStringError(
      std::error_code(errno, std::generic_category()), "could not start %s",
      path.c_str());
}

} // namespace ctk::jit
