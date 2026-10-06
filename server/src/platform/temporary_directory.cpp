#include "ctk/platform/temporary_directory.hpp"

#include <cerrno>
#include <cstdlib>
#include <stdexcept>
#include <string>
#include <system_error>

#include <unistd.h>

namespace ctk::platform {

TemporaryDirectory::TemporaryDirectory(std::string_view prefix) {
  if (prefix.empty() || prefix.find_first_of("/\\") != std::string_view::npos ||
      prefix.find('\0') != std::string_view::npos)
    throw std::invalid_argument("temporary directory prefix must be a name");
  auto pattern = (std::filesystem::temp_directory_path() /
                  (std::string(prefix) + "-XXXXXX"))
                     .string();
  // mkdtemp combines exclusive creation and 0700 permissions on macOS/RHEL.
  if (::mkdtemp(pattern.data()) == nullptr)
    throw std::system_error(errno, std::generic_category(),
                            "cannot create private temporary directory");
  try {
    path_ = pattern;
  } catch (...) {
    std::error_code ignored;
    std::filesystem::remove(pattern, ignored);
    throw;
  }
}

TemporaryDirectory::~TemporaryDirectory() {
  std::error_code ignored;
  std::filesystem::remove_all(path_, ignored);
}

} // namespace ctk::platform
