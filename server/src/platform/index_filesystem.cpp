#include "index_filesystem.hpp"

#ifdef __APPLE__
#include <sys/mount.h>
#include <sys/param.h>
#include <sys/stat.h>
#elif defined(__linux__)
#include <linux/magic.h>
#include <sys/vfs.h>
#endif

#include <algorithm>
#include <atomic>
#include <cstring>
#include <sys/resource.h>

namespace ctk::platform {
namespace {
std::atomic<std::size_t> retained_descriptors{0};
}
bool reserve_index_descriptor() {
  rlimit limit{};
  if (getrlimit(RLIMIT_NOFILE, &limit) != 0 || limit.rlim_cur <= 256)
    return false;
  const auto maximum = std::min<rlim_t>(
      6144, limit.rlim_cur - std::min<rlim_t>(2048, limit.rlim_cur / 2));
  auto current = retained_descriptors.load();
  while (current < maximum)
    if (retained_descriptors.compare_exchange_weak(current, current + 1))
      return true;
  return false;
}
void release_index_descriptor() { retained_descriptors.fetch_sub(1); }

bool supports_index_input_reuse(int descriptor) {
#ifdef __APPLE__
  struct statfs filesystem{};
  if (fstatfs(descriptor, &filesystem) != 0 ||
      (filesystem.f_flags & MNT_LOCAL) == 0)
    return false;
  return std::strcmp(filesystem.f_fstypename, "apfs") == 0 ||
         std::strcmp(filesystem.f_fstypename, "hfs") == 0;
#elif defined(__linux__)
  struct statfs filesystem{};
  if (fstatfs(descriptor, &filesystem) != 0)
    return false;
  switch (static_cast<unsigned long>(filesystem.f_type)) {
  case EXT4_SUPER_MAGIC:
  case XFS_SUPER_MAGIC:
  case BTRFS_SUPER_MAGIC:
  case TMPFS_MAGIC:
  case F2FS_SUPER_MAGIC:
    return true;
  default:
    return false;
  }
#else
  (void)descriptor;
  return false;
#endif
}
} // namespace ctk::platform
