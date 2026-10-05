#include "storage_internal.hpp"

#include <fcntl.h>
#include <sys/file.h>
#include <unistd.h>

#include <stdexcept>
#include <system_error>

namespace ctk::storage::detail {

RootLock::RootLock(const std::filesystem::path &root) {
  std::error_code error;
  std::filesystem::create_directories(root, error);
  if (error)
    throw std::system_error(error, "create storage root");
  const auto lock_path = root / "ownership.lock";
  descriptor_ = ::open(lock_path.c_str(), O_CREAT | O_RDWR, 0600);
  if (descriptor_ < 0)
    throw std::system_error(errno, std::generic_category(), "open ownership lock");
  if (::flock(descriptor_, LOCK_EX | LOCK_NB) != 0) {
    const auto error_number = errno;
    ::close(descriptor_);
    descriptor_ = -1;
    throw std::system_error(error_number, std::generic_category(),
                            "storage root is already owned");
  }
}

RootLock::~RootLock() {
  if (descriptor_ >= 0) {
    ::flock(descriptor_, LOCK_UN);
    ::close(descriptor_);
  }
}

} // namespace ctk::storage::detail
