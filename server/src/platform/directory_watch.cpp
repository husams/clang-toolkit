#include "ctk/platform/directory_watch.hpp"

#include <algorithm>
#include <array>
#include <cerrno>
#include <deque>
#include <fcntl.h>
#include <map>
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
struct DirectoryWatch::Impl {
  int queue = -1;
  std::map<std::filesystem::path, int> directories;
  std::size_t budget = 2048;
  bool add(const std::filesystem::path &resolved);
  Impl() {
#ifdef __APPLE__
    rlimit limit{};
    if (getrlimit(RLIMIT_NOFILE, &limit) != 0)
      return;
    // Keep descriptors available to foreground RPCs. Raising only the soft
    // limit never reduces the existing application allowance.
    if (limit.rlim_cur < 4096) {
      const auto previous = limit.rlim_cur;
      limit.rlim_cur = std::min<rlim_t>(limit.rlim_max, 4096);
      if (setrlimit(RLIMIT_NOFILE, &limit) != 0)
        limit.rlim_cur = previous;
    }
    budget = limit.rlim_cur > 256
                 ? std::min<std::size_t>(2048, (limit.rlim_cur - 256) / 2)
                 : 0;
    queue = kqueue();
    if (queue >= 0)
      fcntl(queue, F_SETFD, FD_CLOEXEC);
#else
    queue = inotify_init1(IN_NONBLOCK | IN_CLOEXEC);
#endif
  }
  ~Impl() {
#ifdef __APPLE__
    for (const auto &[path, descriptor] : directories)
      close(descriptor);
#endif
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
bool DirectoryWatch::Impl::add(const std::filesystem::path &path) {
  if (queue < 0)
    return false;
  if (directories.contains(path))
    return true;
  if (directories.size() >= budget)
    return false;
#ifdef __APPLE__
  const int descriptor = open(path.c_str(), O_EVTONLY | O_CLOEXEC);
  if (descriptor < 0)
    return false;
  struct kevent event;
  EV_SET(&event, descriptor, EVFILT_VNODE, EV_ADD | EV_CLEAR,
         NOTE_WRITE | NOTE_DELETE | NOTE_RENAME | NOTE_REVOKE | NOTE_ATTRIB |
             NOTE_LINK,
         0, nullptr);
  if (kevent(queue, &event, 1, nullptr, 0, nullptr) < 0) {
    close(descriptor);
    return false;
  }
#else
  const int descriptor = inotify_add_watch(
      queue, path.c_str(),
      IN_ONLYDIR | IN_CREATE | IN_DELETE | IN_MOVED_FROM | IN_MOVED_TO |
          IN_DELETE_SELF | IN_MOVE_SELF | IN_ATTRIB);
  if (descriptor < 0)
    return false;
#endif
  directories.emplace(path, descriptor);
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
