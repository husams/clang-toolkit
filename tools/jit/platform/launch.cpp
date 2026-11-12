#include "launch.hpp"
#include "ctk/platform/temporary_directory.hpp"

#include <cerrno>
#include <cstdlib>
#include <optional>
#include <stdexcept>
#include <system_error>
#include <sys/stat.h>
#include <unistd.h>

#include <llvm/ADT/STLExtras.h>
#include <llvm/Support/FileSystem.h>
#include <llvm/Support/raw_ostream.h>

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

bool prepare_private_cache(const std::filesystem::path &path) {
  namespace fs = llvm::sys::fs;
  if (path.empty() || fs::create_directories(path.string(), true, fs::owner_all))
    return false;
  struct stat status {};
  return ::stat(path.c_str(), &status) == 0 && S_ISDIR(status.st_mode) &&
         status.st_uid == ::getuid() && !(status.st_mode & 0022);
}

llvm::Error write_atomic(const std::filesystem::path &path, llvm::StringRef data) {
  auto temporary = (path.parent_path() / ".ctk-jit-XXXXXX").string();
  const int fd = ::mkstemp(temporary.data());
  if (fd < 0)
    return llvm::createStringError(std::error_code(errno, std::generic_category()),
                                   "cannot create a temporary file for %s", path.c_str());
  llvm::raw_fd_ostream stream(fd, true);
  stream << data;
  stream.close();
  auto error = stream.error();
  stream.clear_error();
  if (!error)
    error = llvm::sys::fs::rename(temporary, path.string());
  if (!error)
    return llvm::Error::success();
  llvm::sys::fs::remove(temporary);
  return llvm::createStringError(error, "%s", path.c_str());
}

bool apple_driver_needs_sdk(llvm::ArrayRef<std::string> command,
                            llvm::StringRef directory) {
#ifdef __APPLE__
  if (const auto *sdk = std::getenv("SDKROOT"); sdk && *sdk)
    return false;
  const auto driver = (std::filesystem::path(directory.str()) / command.front())
                          .lexically_normal().string();
  if (driver != "/usr/bin/clang" && driver != "/usr/bin/clang++" &&
      driver != "/usr/bin/cc" && driver != "/usr/bin/c++")
    return false;
  // The system shims discover an SDK through xcrun. The embedded driver needs
  // an equivalent fallback when the project's command leaves it implicit.
  return llvm::none_of(command.drop_front(), [](llvm::StringRef option) {
    return option.starts_with("-isysroot") || option == "--sysroot" ||
           option.starts_with("--sysroot=") || option == "--config" ||
           option.starts_with("--config=");
  });
#else
  (void)command;
  (void)directory;
  return false;
#endif
}

} // namespace ctk::jit
