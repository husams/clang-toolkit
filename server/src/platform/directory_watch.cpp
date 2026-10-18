#include "ctk/platform/directory_watch.hpp"
#include "index_filesystem.hpp"

#include <algorithm>
#include <array>
#include <cerrno>
#include <deque>
#include <fcntl.h>
#include <map>
#include <memory>
#include <mutex>
#include <sys/resource.h>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>
#ifdef __APPLE__
#include <sys/event.h>
#else
#include <sys/inotify.h>
#endif

namespace ctk::platform {
#ifdef __APPLE__
namespace {
struct WatchDescriptor {
  WatchDescriptor() = default;
  WatchDescriptor(const WatchDescriptor &) = delete;
  WatchDescriptor &operator=(const WatchDescriptor &) = delete;
  int fd = -1;
  bool reserved = false;
  ~WatchDescriptor() {
    if (fd >= 0)
      close(fd);
    if (reserved)
      release_index_descriptor();
  }
};
struct WatchDescriptors {
  std::mutex mutex;
  std::map<std::filesystem::path, std::weak_ptr<WatchDescriptor>> paths;
};
std::shared_ptr<WatchDescriptor>
watch_descriptor(const std::filesystem::path &path) {
  static WatchDescriptors pool;
  std::lock_guard lock(pool.mutex);
  if (auto existing = pool.paths.find(path); existing != pool.paths.end()) {
    if (auto handle = existing->second.lock()) {
      struct stat current{}, opened{};
      if (stat(path.c_str(), &current) == 0 &&
          fstat(handle->fd, &opened) == 0 && current.st_dev == opened.st_dev &&
          current.st_ino == opened.st_ino)
        return handle;
    }
  }
  auto handle = std::make_shared<WatchDescriptor>();
  if (!reserve_index_descriptor())
    return {};
  handle->reserved = true;
  handle->fd = open(path.c_str(), O_EVTONLY | O_CLOEXEC);
  if (handle->fd < 0 || !supports_index_input_reuse(handle->fd))
    return {};
  if (pool.paths.size() > 12288)
    std::erase_if(pool.paths,
                  [](const auto &entry) { return entry.second.expired(); });
  pool.paths[path] = handle;
  return handle;
}
} // namespace
#endif

struct DirectoryWatch::Impl {
  int queue = -1;
#ifdef __APPLE__
  std::map<std::filesystem::path, std::shared_ptr<WatchDescriptor>> directories;
  std::size_t files = 0;
#else
  std::map<std::filesystem::path, int> directories;
#endif
  std::size_t budget = 1024;
  bool add(const std::filesystem::path &resolved, bool file = false,
           bool metadata = true);
  Impl() {
#ifdef __APPLE__
    rlimit limit{};
    if (getrlimit(RLIMIT_NOFILE, &limit) != 0)
      return;
    // Keep descriptors available to foreground RPCs. Raising only the soft
    // limit never reduces the existing application allowance.
    if (limit.rlim_cur < 8192) {
      const auto previous = limit.rlim_cur;
      limit.rlim_cur = std::min<rlim_t>(limit.rlim_max, 8192);
      if (setrlimit(RLIMIT_NOFILE, &limit) != 0)
        limit.rlim_cur = previous;
    }
    if (limit.rlim_cur <= 256) {
      budget = 0;
    } else {
      const auto reserve = std::min<rlim_t>(1024, limit.rlim_cur / 2);
      budget = std::min<std::size_t>(
          4096, static_cast<std::size_t>((limit.rlim_cur - reserve) / 2));
    }
    queue = kqueue();
    if (queue >= 0)
      fcntl(queue, F_SETFD, FD_CLOEXEC);
#else
    budget = 4096;
    queue = inotify_init1(IN_NONBLOCK | IN_CLOEXEC);
#endif
  }
  ~Impl() {
    if (queue >= 0)
      close(queue);
  }
};
DirectoryWatch::DirectoryWatch() : impl_(std::make_unique<Impl>()) {}
DirectoryWatch::~DirectoryWatch() = default;
void DirectoryWatch::reset() { impl_ = std::make_unique<Impl>(); }
std::optional<DirectoryWatch::Identity>
DirectoryWatch::identity(const std::filesystem::path &path) {
  struct stat value{};
  if (stat(path.c_str(), &value) || !S_ISDIR(value.st_mode))
    return std::nullopt;
  return Identity{static_cast<std::uint64_t>(value.st_dev),
                  static_cast<std::uint64_t>(value.st_ino)};
}
bool DirectoryWatch::add(const std::filesystem::path &directory) {
  namespace fs = std::filesystem;
  std::error_code error;
  const auto absolute = fs::absolute(directory, error);
  if (error)
    return false;
  auto resolved = absolute.root_path();
  if (!impl_->add(resolved))
    return false;
  const auto relative = absolute.relative_path();
  std::deque<fs::path> parts(relative.begin(), relative.end());
  unsigned symlinks = 0;
  while (!parts.empty()) {
    const auto part = parts.front();
    parts.pop_front();
    if (part == ".")
      continue;
    if (part == "..") {
      resolved = resolved.parent_path();
      continue;
    }
    const auto next = resolved / part;
    const auto status = fs::symlink_status(next, error);
    if (error)
      return false;
    if (fs::is_symlink(status)) {
      // Arm ancestor guards before reading aliases, including links outside
      // the inventory. A final-directory watch alone misses external retargets
      // and ancestor renames whose descendants retain their inode numbers.
      if (++symlinks > 40)
        return false;
      const auto target = fs::read_symlink(next, error);
      if (error)
        return false;
      if (target.is_absolute()) {
        resolved = target.root_path();
        if (!impl_->add(resolved))
          return false;
      }
      const auto suffix = target.relative_path();
      const std::vector<fs::path> components(suffix.begin(), suffix.end());
      for (auto it = components.rbegin(); it != components.rend(); ++it)
        parts.push_front(*it);
    } else {
      if (!fs::is_directory(status) || !impl_->add(next))
        return false;
      resolved = next;
    }
  }
  return true;
}
bool DirectoryWatch::add_directory(const std::filesystem::path &directory) {
  return impl_->add(directory, false, false);
}
bool DirectoryWatch::add_file(const std::filesystem::path &file) {
  return impl_->add(file.parent_path(), false, false) &&
         impl_->add(file, true, false);
}
bool DirectoryWatch::Impl::add(const std::filesystem::path &path, bool file,
                               bool metadata) {
  if (queue < 0)
    return false;
  if (directories.contains(path))
    return true;
  if (directories.size() >= budget)
    return false;
#ifdef __APPLE__
  // Directory inventories must retain capacity even for projects with many
  // thousands of header inputs. Missing file coverage uses the safety sweep.
  if (file && files >= 1024)
    return false;
  auto handle = watch_descriptor(path);
  if (!handle)
    return false;
  const int descriptor = handle->fd;
  struct kevent event;
  EV_SET(&event, descriptor, EVFILT_VNODE, EV_ADD | EV_CLEAR,
         NOTE_WRITE | NOTE_DELETE | NOTE_RENAME | NOTE_REVOKE |
             (metadata ? NOTE_ATTRIB : 0) | NOTE_LINK,
         0, nullptr);
  if (kevent(queue, &event, 1, nullptr, 0, nullptr) < 0)
    return false;
  directories.emplace(path, std::move(handle));
  if (file)
    ++files;
#else
  const int filesystem_descriptor =
      open(path.c_str(), O_RDONLY | (file ? 0 : O_DIRECTORY) | O_CLOEXEC);
  if (filesystem_descriptor < 0)
    return false;
  const bool supported = supports_index_input_reuse(filesystem_descriptor);
  close(filesystem_descriptor);
  if (!supported)
    return false;
  const int descriptor = inotify_add_watch(
      queue, path.c_str(),
      (file ? IN_MODIFY | IN_CLOSE_WRITE : IN_ONLYDIR) | IN_CREATE | IN_DELETE |
          IN_MOVED_FROM | IN_MOVED_TO | IN_DELETE_SELF | IN_MOVE_SELF |
          (metadata ? IN_ATTRIB : 0));
  if (descriptor < 0)
    return false;
#endif
#ifndef __APPLE__
  directories.emplace(path, descriptor);
#endif
  return true;
}
bool DirectoryWatch::changed() {
  if (impl_->queue < 0)
    return false; // add() also fails: callers use uncached directory walks.
#ifdef __APPLE__
  struct kevent event;
  const timespec immediate{};
  int count;
  do {
    count = kevent(impl_->queue, nullptr, 0, &event, 1, &immediate);
  } while (count < 0 && errno == EINTR);
  return count != 0;
#else
  alignas(inotify_event) std::array<char, 4096> events;
  ssize_t count;
  do {
    count = read(impl_->queue, events.data(), events.size());
  } while (count < 0 && errno == EINTR);
  // Any event, including overflow/ignored watches, forces a complete rebuild.
  return count >= 0 || (errno != EAGAIN && errno != EWOULDBLOCK);
#endif
}
} // namespace ctk::platform
