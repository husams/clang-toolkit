#include "index_input_watch.hpp"

#include <algorithm>
#include <atomic>
#include <cerrno>
#include <condition_variable>
#include <map>
#include <mutex>
#include <set>
#include <string>
#include <thread>
#include <utility>
#include <vector>

#include <sys/stat.h>
#ifdef __APPLE__
#include <CoreServices/CoreServices.h>
#else
#include <sys/inotify.h>
#include <unistd.h>
#endif

namespace ctk::platform {
namespace fs = std::filesystem;
namespace {
fs::path absolute_path(const fs::path &path) {
  std::error_code error;
  auto value = fs::absolute(path, error);
  return (error ? path : value).lexically_normal();
}

// Resolve the containing directory, not the final component. This maps aliases
// such as /tmp to their actual parent while preserving a watched symlink entry.
fs::path entry_path(const fs::path &path) {
  const auto absolute = absolute_path(path);
  std::error_code error;
  auto parent = fs::weakly_canonical(absolute.parent_path(), error);
  if (error)
    parent = absolute.parent_path();
  return (parent / absolute.filename()).lexically_normal();
}

fs::path resolved_path(const fs::path &path) {
  std::error_code error;
  auto value = fs::weakly_canonical(absolute_path(path), error);
  return (error ? absolute_path(path) : value).lexically_normal();
}

fs::path closest_existing_directory(fs::path path) {
  std::error_code error;
  while (!path.empty() && !fs::is_directory(path, error)) {
    error.clear();
    const auto parent = path.parent_path();
    if (parent == path)
      return {};
    path = parent;
  }
  return path;
}

std::set<fs::path> symlink_ancestors(const fs::path &path) {
  std::set<fs::path> result;
  const auto absolute = absolute_path(path);
  auto current = absolute.root_path();
  for (const auto &part : absolute.relative_path()) {
    current /= part;
#ifdef __APPLE__
    if (current == fs::path("/tmp") || current == fs::path("/var") ||
        current == fs::path("/etc"))
      continue;
#endif
    std::error_code error;
    if (fs::is_symlink(fs::symlink_status(current, error)))
      result.insert(entry_path(current));
  }
  return result;
}

bool is_same_or_child(const fs::path &path, const fs::path &parent) {
  auto p = path.begin();
  for (auto part = parent.begin(); part != parent.end(); ++part, ++p)
    if (p == path.end() || *p != *part)
      return false;
  return true;
}

void add_compact_root(std::set<fs::path> &roots, const fs::path &candidate) {
  if (candidate.empty())
    return;
  auto normalized = candidate.lexically_normal();
  if (normalized == normalized.root_path())
    return;
  for (const auto &existing : roots)
    if (is_same_or_child(normalized, existing))
      return;
  std::erase_if(roots, [&](const fs::path &existing) {
    return is_same_or_child(existing, normalized);
  });
  roots.insert(normalized);
}
} // namespace

struct IndexInputWatch::Impl {
  mutable std::mutex mutex;
  std::set<fs::path> files;
  std::set<fs::path> directories;
  std::set<fs::path> symlinks;
  std::set<fs::path> path_ancestors;
  bool armed = false;
  bool pending_change = false;
  bool available = false;
#ifdef __APPLE__
  FSEventStreamRef stream = nullptr;
  CFRunLoopRef run_loop = nullptr;
  CFRunLoopSourceRef source = nullptr;
  std::thread thread;
  bool ready = false;
  bool stopping = false;
  bool reconfigure = false;
  bool registrations_dirty = false;
  bool ever_started = false;
  std::uint64_t requested_generation = 0;
  std::uint64_t configured_generation = 0;
  bool has_registration_floor = false;
  FSEventStreamEventId registration_floor = 0;
  FSEventStreamEventId last_event_id = FSEventsGetCurrentEventId();
#else
  int fd = -1;
  std::map<fs::path, int> watched_paths;
  std::map<int, fs::path> watched_directories;
#endif

  Impl() {
#ifdef __APPLE__
    thread = std::thread([this] { run_loop_main(); });
    std::unique_lock lock(mutex);
    ready_cv.wait(lock, [&] { return ready; });
#else
    fd = inotify_init1(IN_NONBLOCK | IN_CLOEXEC);
    available = fd >= 0;
#endif
  }

  ~Impl() {
#ifdef __APPLE__
    {
      std::lock_guard lock(mutex);
      stopping = true;
    }
    wake_run_loop();
    if (thread.joinable())
      thread.join();
    if (source)
      CFRelease(source);
    if (run_loop)
      CFRelease(run_loop);
#else
    if (fd >= 0)
      close(fd);
#endif
  }

  bool add_file(const fs::path &input) {
    const auto alias = entry_path(input);
    const auto resolved = resolved_path(input);
    const auto links = symlink_ancestors(input);
#ifdef __APPLE__
    if (alias.parent_path() == alias.root_path())
      return false;
#endif
    std::lock_guard lock(mutex);
#ifdef __APPLE__
    if (!files.contains(alias) ||
        (resolved != alias && !files.contains(resolved)) ||
        std::any_of(links.begin(), links.end(),
                    [&](const auto &link) { return !symlinks.contains(link); }))
      note_registration(FSEventsGetCurrentEventId());
#endif
    const bool inserted = files.insert(alias).second;
    bool link_inserted = false;
    for (const auto &link : links) {
      link_inserted = symlinks.insert(link).second || link_inserted;
      if (link_inserted)
        add_ancestors(link);
    }
    const bool resolved_inserted =
        resolved != alias && files.insert(resolved).second;
    if (inserted)
      add_ancestors(alias);
    if (resolved_inserted)
      add_ancestors(resolved);
#ifndef __APPLE__
    if (!watch_ancestor_chain(alias.parent_path()))
      return false;
    if (resolved != alias && !watch_ancestor_chain(resolved.parent_path()))
      return false;
    for (const auto &link : links)
      if (!watch_ancestor_chain(link.parent_path()))
        return false;
#else
    if (inserted || resolved_inserted || link_inserted)
      registrations_dirty = true;
#endif
    return inserted || resolved_inserted || files.contains(alias);
  }

  bool add_directory(const fs::path &input) {
    const auto alias = entry_path(input);
    const auto resolved = resolved_path(input);
    const auto links = symlink_ancestors(input);
#ifdef __APPLE__
    if (alias == alias.root_path())
      return false;
#endif
    std::lock_guard lock(mutex);
#ifdef __APPLE__
    if (!directories.contains(alias) || !directories.contains(resolved) ||
        std::any_of(links.begin(), links.end(),
                    [&](const auto &link) { return !symlinks.contains(link); }))
      note_registration(FSEventsGetCurrentEventId());
#endif
    const bool inserted = directories.insert(alias).second;
    const bool resolved_inserted = directories.insert(resolved).second;
    bool link_inserted = false;
    for (const auto &link : links) {
      link_inserted = symlinks.insert(link).second || link_inserted;
      if (link_inserted)
        add_ancestors(link);
    }
    if (inserted)
      add_ancestors(alias);
    if (resolved_inserted)
      add_ancestors(resolved);
#ifndef __APPLE__
    if (!watch_ancestor_chain(alias.parent_path()) ||
        !watch_ancestor_chain(resolved))
      return false;
    if (resolved != alias && !watch_ancestor_chain(resolved.parent_path()))
      return false;
    for (const auto &link : links)
      if (!watch_ancestor_chain(link.parent_path()))
        return false;
#else
    if (inserted || resolved_inserted || link_inserted)
      registrations_dirty = true;
#endif
    return true;
  }

  void add_ancestors(const fs::path &path) {
    auto parent = path.parent_path();
    while (!parent.empty() && parent != parent.root_path()) {
      path_ancestors.insert(parent);
      const auto next = parent.parent_path();
      if (next == parent)
        break;
      parent = next;
    }
  }

  bool arm() {
#ifdef __APPLE__
    std::unique_lock lock(mutex);
    const bool first_arm = !armed;
    armed = true;
    if (first_arm || registrations_dirty ||
        configured_generation < requested_generation) {
      if (first_arm || registrations_dirty) {
        registrations_dirty = false;
        request_reconfigure();
      }
      const auto requested = requested_generation;
      ready_cv.wait(
          lock, [&] { return configured_generation >= requested || stopping; });
    }
    return available;
#else
    std::lock_guard lock(mutex);
    armed = true;
    available = fd >= 0;
    return available;
#endif
  }

  bool changed() {
#ifndef __APPLE__
    if (fd < 0)
      return false;
    alignas(inotify_event) char buffer[65536];
    bool changed = false;
    for (;;) {
      const auto count = read(fd, buffer, sizeof(buffer));
      if (count < 0) {
        if (errno == EINTR)
          continue;
        if (errno != EAGAIN && errno != EWOULDBLOCK)
          changed = true;
        break;
      }
      if (count == 0)
        break;
      for (std::size_t offset = 0; offset < static_cast<std::size_t>(count);) {
        const auto *event =
            reinterpret_cast<const inotify_event *>(buffer + offset);
        offset += sizeof(inotify_event) + event->len;
        if (event->mask & (IN_Q_OVERFLOW | IN_IGNORED | IN_DELETE_SELF |
                           IN_MOVE_SELF | IN_UNMOUNT)) {
          changed = true;
          continue;
        }
        std::lock_guard lock(mutex);
        const auto watched = watched_directories.find(event->wd);
        if (watched == watched_directories.end()) {
          changed = true;
          continue;
        }
        const auto changed_path =
            event->len && event->name[0]
                ? (watched->second / event->name).lexically_normal()
                : watched->second;
        constexpr std::uint32_t entry_mask =
            IN_CREATE | IN_DELETE | IN_MOVED_FROM | IN_MOVED_TO;
        constexpr std::uint32_t file_mask =
            entry_mask | IN_CLOSE_WRITE | IN_MODIFY;
        if ((files.contains(changed_path) && (event->mask & file_mask)) ||
            (symlinks.contains(changed_path) && (event->mask & entry_mask))) {
          changed = true;
          continue;
        }
        if (path_ancestors.contains(changed_path) &&
            (event->mask & entry_mask) && (event->mask & IN_ISDIR)) {
          changed = true;
          continue;
        }
        if ((event->mask & entry_mask) &&
            directories.contains(changed_path.parent_path()))
          changed = true;
        else if ((event->mask & entry_mask) &&
                 directories.contains(changed_path))
          changed = true;
      }
    }
    return changed;
#else
    bool needs_arm = false;
    {
      std::lock_guard lock(mutex);
      needs_arm = armed && registrations_dirty;
    }
    if (needs_arm)
      arm();
    std::lock_guard lock(mutex);
    const bool result = std::exchange(pending_change, false);
    return result;
#endif
  }

#ifndef __APPLE__
  bool watch_ancestor_chain(const fs::path &path) {
    auto current = closest_existing_directory(path);
    if (current.empty() || current == current.root_path())
      return false;
    while (!current.empty() && current != current.root_path()) {
      if (!watch_directory(current))
        return false;
      const auto parent = current.parent_path();
      if (parent == current.root_path())
        break;
      current = parent;
    }
    return !current.empty();
  }

  bool watch_directory(const fs::path &path) {
    if (fd < 0)
      return false;
    const auto normalized = resolved_path(path);
    if (normalized.empty())
      return false;
    if (watched_paths.contains(normalized))
      return true;
    constexpr std::uint32_t mask = IN_ONLYDIR | IN_CLOSE_WRITE | IN_MODIFY |
                                   IN_CREATE | IN_DELETE | IN_MOVED_FROM |
                                   IN_MOVED_TO | IN_DELETE_SELF | IN_MOVE_SELF |
                                   IN_UNMOUNT | IN_EXCL_UNLINK;
    const int wd = inotify_add_watch(fd, normalized.c_str(), mask);
    if (wd < 0)
      return false;
    watched_paths.insert_or_assign(normalized, wd);
    watched_directories.insert_or_assign(wd, normalized);
    return true;
  }
#else
  std::condition_variable ready_cv;

  void note_registration(FSEventStreamEventId floor) {
    if (!has_registration_floor) {
      registration_floor = floor;
      if (!armed)
        last_event_id = floor;
      has_registration_floor = true;
    } else {
      registration_floor = std::min(registration_floor, floor);
      if (!armed)
        last_event_id = std::min(last_event_id, floor);
    }
  }

  void request_reconfigure() {
    reconfigure = true;
    ++requested_generation;
    wake_run_loop_unlocked();
  }

  static void source_perform(void *info) {
    auto *self = static_cast<Impl *>(info);
    self->configure_stream();
  }

  static void event_callback(ConstFSEventStreamRef, void *info, size_t count,
                             void *paths, const FSEventStreamEventFlags flags[],
                             const FSEventStreamEventId ids[]) {
    auto *self = static_cast<Impl *>(info);
    auto **event_paths = static_cast<char **>(paths);
    std::lock_guard lock(self->mutex);
    constexpr FSEventStreamEventFlags global_flags =
        kFSEventStreamEventFlagUserDropped |
        kFSEventStreamEventFlagKernelDropped |
        kFSEventStreamEventFlagEventIdsWrapped |
        kFSEventStreamEventFlagRootChanged;
    constexpr FSEventStreamEventFlags file_flags =
        kFSEventStreamEventFlagItemModified |
        kFSEventStreamEventFlagItemCreated |
        kFSEventStreamEventFlagItemRemoved | kFSEventStreamEventFlagItemRenamed;
    constexpr FSEventStreamEventFlags entry_flags =
        kFSEventStreamEventFlagItemCreated |
        kFSEventStreamEventFlagItemRemoved | kFSEventStreamEventFlagItemRenamed;
    for (size_t i = 0; i < count; ++i) {
      self->last_event_id = std::max(self->last_event_id, ids[i]);
      if (flags[i] & global_flags) {
        self->pending_change = true;
        continue;
      }
      const fs::path changed_path(event_paths[i]);
      const bool needs_scan = flags[i] & kFSEventStreamEventFlagMustScanSubDirs;
      if ((self->files.contains(changed_path) && (flags[i] & file_flags)) ||
          (self->symlinks.contains(changed_path) && (flags[i] & entry_flags))) {
        self->pending_change = true;
        continue;
      }
      if ((((flags[i] & entry_flags) || needs_scan) &&
           (self->directories.contains(changed_path) ||
            self->directories.contains(changed_path.parent_path()))) ||
          (needs_scan && self->path_ancestors.contains(changed_path)))
        self->pending_change = true;
    }
  }

  void wake_run_loop_unlocked() {
    if (source)
      CFRunLoopSourceSignal(source);
    if (run_loop)
      CFRunLoopWakeUp(run_loop);
  }
  void wake_run_loop() {
    std::lock_guard lock(mutex);
    wake_run_loop_unlocked();
  }

  void run_loop_main() {
    run_loop = CFRunLoopGetCurrent();
    CFRetain(run_loop);
    CFRunLoopSourceContext context{};
    context.info = this;
    context.perform = &Impl::source_perform;
    source = CFRunLoopSourceCreate(kCFAllocatorDefault, 0, &context);
    CFRunLoopAddSource(run_loop, source, kCFRunLoopDefaultMode);
    {
      std::lock_guard lock(mutex);
      ready = true;
    }
    ready_cv.notify_one();
    CFRunLoopRun();
    if (stream) {
      FSEventStreamStop(stream);
      FSEventStreamInvalidate(stream);
      FSEventStreamRelease(stream);
      stream = nullptr;
    }
  }

  void configure_stream() {
    std::vector<fs::path> roots;
    FSEventStreamEventId since = 0;
    std::uint64_t generation = 0;
    {
      std::lock_guard lock(mutex);
      if (stopping) {
        configured_generation = requested_generation;
        ready_cv.notify_all();
        CFRunLoopStop(run_loop);
        return;
      }
      if (!reconfigure || !armed)
        return;
      reconfigure = false;
      generation = requested_generation;
      since = last_event_id;
      if (has_registration_floor) {
        since = ever_started ? std::min(since, registration_floor)
                             : registration_floor;
      }
      has_registration_floor = false;
      std::set<fs::path> compact;
      for (const auto &file : files)
        add_compact_root(compact,
                         closest_existing_directory(file.parent_path()));
      for (const auto &link : symlinks)
        add_compact_root(compact,
                         closest_existing_directory(link.parent_path()));
      for (const auto &directory : directories) {
        const auto existing = closest_existing_directory(directory);
        add_compact_root(compact, existing);
        add_compact_root(compact,
                         closest_existing_directory(directory.parent_path()));
      }
      roots.assign(compact.begin(), compact.end());
    }
    if (stream) {
      FSEventStreamStop(stream);
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
      FSEventStreamUnscheduleFromRunLoop(stream, run_loop,
                                         kCFRunLoopDefaultMode);
#pragma clang diagnostic pop
      FSEventStreamInvalidate(stream);
      FSEventStreamRelease(stream);
      stream = nullptr;
    }
    if (roots.empty()) {
      std::lock_guard lock(mutex);
      available = false;
      configured_generation = generation;
      ready_cv.notify_all();
      return;
    }
    std::vector<const void *> values;
    values.reserve(roots.size());
    for (const auto &root : roots) {
      auto *value = CFStringCreateWithFileSystemRepresentation(
          kCFAllocatorDefault, root.c_str());
      if (!value)
        continue;
      values.push_back(value);
    }
    CFArrayRef paths = CFArrayCreate(kCFAllocatorDefault, values.data(),
                                     static_cast<CFIndex>(values.size()),
                                     &kCFTypeArrayCallBacks);
    for (const auto *value : values)
      CFRelease(value);
    if (!paths || CFArrayGetCount(paths) == 0) {
      if (paths)
        CFRelease(paths);
      std::lock_guard lock(mutex);
      available = false;
      configured_generation = generation;
      ready_cv.notify_all();
      return;
    }
    FSEventStreamContext context{};
    context.info = this;
    stream = FSEventStreamCreate(kCFAllocatorDefault, &Impl::event_callback,
                                 &context, paths, since, 0.15,
                                 kFSEventStreamCreateFlagFileEvents |
                                     kFSEventStreamCreateFlagWatchRoot |
                                     kFSEventStreamCreateFlagNoDefer);
    CFRelease(paths);
    if (!stream) {
      std::lock_guard lock(mutex);
      available = false;
      configured_generation = generation;
      ready_cv.notify_all();
      return;
    }
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
    FSEventStreamScheduleWithRunLoop(stream, run_loop, kCFRunLoopDefaultMode);
#pragma clang diagnostic pop
    if (!FSEventStreamStart(stream)) {
      FSEventStreamInvalidate(stream);
      FSEventStreamRelease(stream);
      stream = nullptr;
      std::lock_guard lock(mutex);
      available = false;
    } else {
      std::lock_guard lock(mutex);
      ever_started = true;
      available = true;
    }
    {
      std::lock_guard lock(mutex);
      configured_generation = generation;
    }
    ready_cv.notify_all();
  }
#endif
};

IndexInputWatch::IndexInputWatch() : impl_(std::make_unique<Impl>()) {}
IndexInputWatch::~IndexInputWatch() = default;
bool IndexInputWatch::add_file(const fs::path &path) {
  return impl_->add_file(path);
}
bool IndexInputWatch::add_directory(const fs::path &path) {
  return impl_->add_directory(path);
}
bool IndexInputWatch::arm() { return impl_->arm(); }
bool IndexInputWatch::changed() { return impl_->changed(); }
void IndexInputWatch::reset() { impl_ = std::make_unique<Impl>(); }
} // namespace ctk::platform
