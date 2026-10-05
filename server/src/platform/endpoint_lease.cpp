#include "ctk/platform/endpoint_lease.hpp"
#include <fcntl.h>
#include <filesystem>
#include <stdexcept>
#include <sys/file.h>
#include <unistd.h>

namespace ctk::platform {
EndpointLease::EndpointLease(const std::string &endpoint) {
  std::filesystem::path pathname;
  if (endpoint.starts_with("unix://")) {
    pathname = endpoint.substr(7) + ".lock";
  } else {
    // A port-wide lease also covers localhost/IPv4/IPv6 aliases, while leaving
    // gRPC's own transport tuning defaults untouched.
    pathname =
        std::filesystem::temp_directory_path() /
        ("ctk-tcp-" + endpoint.substr(endpoint.rfind(':') + 1) + ".lock");
  }
  descriptor_ = ::open(pathname.c_str(), O_CREAT | O_RDWR | O_CLOEXEC, 0600);
  if (descriptor_ < 0)
    throw std::runtime_error("cannot acquire endpoint ownership: " +
                             pathname.string());
  if (::flock(descriptor_, LOCK_EX | LOCK_NB) != 0) {
    ::close(descriptor_);
    descriptor_ = -1;
    throw std::runtime_error("another clang-toolkit server owns " + endpoint);
  }
}
EndpointLease::~EndpointLease() {
  // Leave the empty lock file in place: unlinking it would allow a competing
  // process to lock a different inode. The OS releases ownership on exit.
  if (descriptor_ >= 0)
    ::close(descriptor_);
}
} // namespace ctk::platform
