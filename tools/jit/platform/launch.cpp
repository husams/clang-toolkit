#include "launch.hpp"
#include "ctk/platform/temporary_directory.hpp"

#include <cerrno>
#include <cstdlib>
#include <optional>
#include <stdexcept>
#include <system_error>
#include <unistd.h>

namespace ctk::jit {
namespace {

std::optional<std::filesystem::path> configured_state_root() {
  namespace fs = std::filesystem;
  if (const auto *path = std::getenv("CTK_JIT_STATE_DIR"); path && *path)
    return fs::absolute(path);
  if (const auto *path = std::getenv("XDG_STATE_HOME"); path && *path)
    return fs::path(path) / "ctk-jit";
  if (const auto *home = std::getenv("HOME"); home && *home)
    return fs::path(home) / ".local/state/ctk-jit";
  return std::nullopt;
}

} // namespace

std::filesystem::path state_root() {
  if (auto root = configured_state_root())
    return *root;
  throw std::runtime_error("set CTK_JIT_STATE_DIR to use indexes or durable batches");
}

void configure_ast_cache() {
  // The reused Clang engine initializes its store once per process. Point it
  // at JIT state before any worker starts, regardless of the server's settings.
  auto root = configured_state_root();
  if (!root) {
    static const platform::TemporaryDirectory temporary("ctk-jit");
    root = temporary.path();
  }
  const auto cache = *root / "ast-cache";
  if (::setenv("CTK_STORAGE_ROOT", cache.c_str(), 1) != 0)
    throw std::system_error(errno, std::generic_category(), "configure CTK JIT AST cache");
}

llvm::Error launch_cli(llvm::StringRef executable, char **argv) {
  const auto path = executable.str();
  ::execv(path.c_str(), argv);
  return llvm::createStringError(
      std::error_code(errno, std::generic_category()), "could not start %s",
      path.c_str());
}

} // namespace ctk::jit
