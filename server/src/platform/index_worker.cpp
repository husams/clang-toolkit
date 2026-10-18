#include "ctk/platform/index_worker.hpp"

#include <algorithm>
#include <cerrno>
#include <chrono>
#include <csignal>
#include <cstddef>
#include <cstdint>
#include <fcntl.h>
#include <fstream>
#include <iterator>
#include <map>
#include <spawn.h>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/resource.h>
#include <sys/wait.h>
#include <system_error>
#include <thread>
#include <unistd.h>
#include <vector>

#ifdef __APPLE__
#include <libproc.h>
#include <mach-o/dyld.h>
#include <pthread.h>
#include <sys/sysctl.h>
#else
#include <sched.h>
#include <sys/syscall.h>
#include <sys/sysinfo.h>
#endif

extern char **environ;

namespace ctk::platform {

namespace {
constexpr std::size_t kMaximumIndexWorkers = 4;
constexpr std::uint64_t kGiB = 1024ULL * 1024 * 1024;
constexpr std::uint64_t kWorkerMemoryBudget = 1536ULL * 1024 * 1024;
constexpr std::uint64_t kWorkerOutputBudget = 128ULL * 1024 * 1024;
constexpr std::uint64_t kControllerMemoryBudget = kGiB;
constexpr std::uint64_t kMinimumSystemReserve = 4 * kGiB;
// macOS may report EPERM for a process group whose last member just exited.
// Give waitpid a brief chance to confirm that race; a live child still fails.
constexpr auto kSignalFailureExitWindow = std::chrono::milliseconds(10);

struct CgroupMount {
  std::filesystem::path root;
  std::filesystem::path point;
  bool unified = false;
  std::string controllers;
};

std::string unescape_mount_field(std::string value) {
  for (const auto &[escaped, character] :
       {std::pair{"\\040", ' '}, std::pair{"\\011", '\t'},
        std::pair{"\\134", '\\'}}) {
    std::size_t position = 0;
    while ((position = value.find(escaped, position)) != std::string::npos) {
      value.replace(position, 4, 1, character);
      ++position;
    }
  }
  return value;
}

std::vector<std::string> split_words(const std::string &line) {
  std::istringstream stream(line);
  std::vector<std::string> words;
  for (std::string word; stream >> word;)
    words.push_back(std::move(word));
  return words;
}

std::map<std::string, std::string>
cgroup_memberships(std::string_view contents) {
  std::istringstream input{std::string(contents)};
  std::map<std::string, std::string> memberships;
  for (std::string line; std::getline(input, line);) {
    const auto first = line.find(':');
    const auto second =
        line.find(':', first == std::string::npos ? first : first + 1);
    if (first == std::string::npos || second == std::string::npos)
      continue;
    const auto controllers = line.substr(first + 1, second - first - 1);
    const auto path = line.substr(second + 1);
    if (controllers.empty())
      memberships["unified"] = path;
    else {
      std::istringstream list(controllers);
      for (std::string controller; std::getline(list, controller, ',');)
        memberships[controller] = path;
    }
  }
  return memberships;
}

std::vector<CgroupMount> cgroup_mounts(std::string_view contents) {
  std::istringstream input{std::string(contents)};
  std::vector<CgroupMount> mounts;
  for (std::string line; std::getline(input, line);) {
    const auto separator = line.find(" - ");
    if (separator == std::string::npos)
      continue;
    const auto left = split_words(line.substr(0, separator));
    const auto right = split_words(line.substr(separator + 3));
    if (left.size() < 5 || right.size() < 3 ||
        (right[0] != "cgroup" && right[0] != "cgroup2"))
      continue;
    mounts.push_back({unescape_mount_field(left[3]),
                      unescape_mount_field(left[4]), right[0] == "cgroup2",
                      right[2]});
  }
  return mounts;
}

bool has_controller(const CgroupMount &mount, const std::string &controller) {
  std::istringstream list(mount.controllers);
  for (std::string value; std::getline(list, value, ',');)
    if (value == controller)
      return true;
  return false;
}

std::optional<std::filesystem::path>
cgroup_directory(const CgroupMount &mount, const std::string &membership) {
  const std::filesystem::path member(membership);
  const auto relative = member.lexically_relative(mount.root);
  std::vector<std::filesystem::path> candidates;
  if (member == mount.root ||
      (relative != "." && !relative.empty() && *relative.begin() != ".."))
    candidates.push_back(mount.point / relative);
  // In a cgroup namespace, /proc/self/cgroup can be relative to the namespace
  // root while mountinfo records the host-side root.
  candidates.push_back(mount.point / member.relative_path());
  for (const auto &candidate : candidates) {
    std::error_code error;
    if (std::filesystem::is_directory(candidate, error))
      return candidate;
  }
  return std::nullopt;
}

template <class Apply>
bool visit_cgroup_ancestors(const CgroupMount &mount,
                            const std::filesystem::path &leaf,
                            const char *filename, Apply apply) {
  auto directory = leaf;
  for (;;) {
    std::ifstream input(directory / filename);
    std::string value;
    if (!input) {
      // A mounted cgroup v2 root can omit a controller file when that
      // controller is not enabled for the root itself. A missing file on the
      // current cgroup or any intermediate group leaves the budget unknown.
      if (index_worker_detail::missing_cgroup_limit_is_unlimited(
              mount.unified, directory == mount.point))
        return true;
      return false;
    }
    std::string contents;
    if (!std::getline(input, contents) ||
        !(value = index_worker_detail::cgroup_limit_line(contents)).size() ||
        !apply(value))
      return false;
    if (directory == mount.point)
      return true;
    const auto parent = directory.parent_path();
    if (parent == directory || parent.lexically_relative(mount.point).empty())
      return false;
    directory = parent;
  }
}

std::size_t effective_cgroup_parallelism(std::size_t cpus, std::uint64_t memory,
                                         std::string_view membership_text,
                                         std::string_view mountinfo_text) {
  const auto memberships = cgroup_memberships(membership_text);
  const auto mounts = cgroup_mounts(mountinfo_text);
  bool read_memory_hierarchy = false;
  bool read_cpu_hierarchy = false;
  for (const auto &mount : mounts) {
    const std::string memory_key = mount.unified ? "unified" : "memory";
    const auto memory_member = memberships.find(memory_key);
    if (memory_member != memberships.end() &&
        (mount.unified || has_controller(mount, memory_key))) {
      const auto directory = cgroup_directory(mount, memory_member->second);
      if (!directory)
        return 1;
      const char *file = mount.unified ? "memory.max" : "memory.limit_in_bytes";
      if (!visit_cgroup_ancestors(
              mount, *directory, file, [&](const std::string &value) {
                if (value == "max")
                  return true;
                const auto limit =
                    index_worker_detail::parse_memory_limit(value);
                if (!limit)
                  return false;
                memory = std::min(memory, *limit);
                return true;
              }))
        return 1;
      read_memory_hierarchy = true;
    }

    const std::string cpu_key = mount.unified ? "unified" : "cpu";
    const auto cpu_member = memberships.find(cpu_key);
    if (cpu_member == memberships.end() ||
        (!mount.unified && !has_controller(mount, cpu_key)))
      continue;
    const auto directory = cgroup_directory(mount, cpu_member->second);
    if (!directory)
      return 1;
    if (mount.unified) {
      if (!visit_cgroup_ancestors(
              mount, *directory, "cpu.max", [&](const std::string &value) {
                if (value.starts_with("max ")) {
                  std::istringstream input(value);
                  std::string marker, trailing;
                  std::uint64_t period = 0;
                  return (input >> marker >> period) && marker == "max" &&
                         period && !(input >> trailing);
                }
                const auto quota = index_worker_detail::parse_cpu_quota(value);
                if (quota)
                  cpus = std::min(cpus, *quota);
                return quota.has_value();
              }))
        return 1;
    } else {
      auto ancestor = *directory;
      for (;;) {
        std::ifstream quota_input(ancestor / "cpu.cfs_quota_us");
        std::ifstream period_input(ancestor / "cpu.cfs_period_us");
        long long quota = -1;
        std::uint64_t period = 0;
        if (!quota_input || !period_input || !(quota_input >> quota) ||
            !(period_input >> period) || !period)
          return 1;
        if (quota > 0)
          cpus =
              std::min(cpus, std::max<std::size_t>(
                                 1, static_cast<std::size_t>(quota / period)));
        if (ancestor == mount.point)
          break;
        const auto parent = ancestor.parent_path();
        if (parent == ancestor ||
            parent.lexically_relative(mount.point).empty())
          return 1;
        ancestor = parent;
      }
    }
    read_cpu_hierarchy = true;
  }
  if (!read_memory_hierarchy || !read_cpu_hierarchy || !cpus || !memory)
    return 1;
  return index_worker_detail::parallelism_limit(cpus, memory);
}

std::optional<std::uint64_t> physical_memory_bytes() {
#ifdef __APPLE__
  std::uint64_t bytes = 0;
  std::size_t size = sizeof(bytes);
  if (sysctlbyname("hw.memsize", &bytes, &size, nullptr, 0) != 0 || !bytes)
    return std::nullopt;
  return bytes;
#elif defined(__linux__)
  struct sysinfo information{};
  if (sysinfo(&information) != 0 || !information.totalram ||
      !information.mem_unit)
    return std::nullopt;
  const auto bytes = static_cast<std::uint64_t>(information.totalram) *
                     static_cast<std::uint64_t>(information.mem_unit);
  return bytes ? std::optional<std::uint64_t>(bytes) : std::nullopt;
#else
  return std::nullopt;
#endif
}
} // namespace

std::optional<std::uint64_t>
index_worker_detail::parse_memory_limit(std::string_view value) {
  if (value.empty() || value == "max")
    return std::nullopt;
  std::uint64_t bytes = 0;
  for (const char character : value) {
    if (character < '0' || character > '9' ||
        bytes > (UINT64_MAX - static_cast<unsigned>(character - '0')) / 10)
      return std::nullopt;
    bytes = bytes * 10 + static_cast<unsigned>(character - '0');
  }
  return bytes ? std::optional<std::uint64_t>(bytes) : std::nullopt;
}

std::string index_worker_detail::cgroup_limit_line(std::string_view contents) {
  const auto end = contents.find_first_of("\r\n");
  contents = contents.substr(0, end);
  const auto first = contents.find_first_not_of(" \t");
  if (first == std::string_view::npos)
    return {};
  const auto last = contents.find_last_not_of(" \t");
  return std::string(contents.substr(first, last - first + 1));
}

std::size_t index_worker_detail::cgroup_parallelism_limit(
    std::size_t host_cpus, std::uint64_t host_memory,
    std::string_view memberships, std::string_view mountinfo) {
  return effective_cgroup_parallelism(host_cpus, host_memory, memberships,
                                      mountinfo);
}

bool index_worker_detail::missing_cgroup_limit_is_unlimited(bool unified,
                                                            bool mount_root) {
  return unified && mount_root;
}

std::optional<std::size_t>
index_worker_detail::parse_cpu_quota(std::string_view value) {
  std::istringstream input{std::string(value)};
  std::string quota_text, trailing;
  std::uint64_t period = 0;
  if (!(input >> quota_text >> period) || !period || quota_text == "max" ||
      (input >> trailing))
    return std::nullopt;
  const auto quota = parse_memory_limit(quota_text);
  if (!quota)
    return std::nullopt;
  return std::max<std::size_t>(1, static_cast<std::size_t>(*quota / period));
}

std::size_t
index_worker_detail::parallelism_limit(std::size_t logical_cpus,
                                       std::uint64_t physical_memory_bytes) {
  if (!logical_cpus || !physical_memory_bytes)
    return 1;
  const auto cpu_slots = logical_cpus > 2 ? logical_cpus - 2 : 1;
  const auto reserve =
      std::max(physical_memory_bytes / 2, kMinimumSystemReserve) +
      kControllerMemoryBudget;
  if (physical_memory_bytes <= reserve)
    return 1;
  const auto memory_slots = (physical_memory_bytes - reserve) /
                            (kWorkerMemoryBudget + kWorkerOutputBudget);
  return std::max<std::size_t>(
      1, std::min({cpu_slots, static_cast<std::size_t>(memory_slots),
                   kMaximumIndexWorkers}));
}

std::size_t index_worker_parallelism_limit() {
  const auto memory = physical_memory_bytes();
  if (!memory)
    return 1;
#ifdef __APPLE__
  const auto logical_cpus = sysconf(_SC_NPROCESSORS_ONLN);
  if (logical_cpus <= 0)
    return 1;
  return index_worker_detail::parallelism_limit(
      static_cast<std::size_t>(logical_cpus), *memory);
#elif defined(__linux__)
  cpu_set_t affinity;
  CPU_ZERO(&affinity);
  if (sched_getaffinity(0, sizeof(affinity), &affinity) != 0)
    return 1;
  std::ifstream membership_file("/proc/self/cgroup");
  std::ifstream mountinfo_file("/proc/self/mountinfo");
  if (!membership_file || !mountinfo_file)
    return 1;
  const std::string memberships(
      (std::istreambuf_iterator<char>(membership_file)), {});
  const std::string mountinfo((std::istreambuf_iterator<char>(mountinfo_file)),
                              {});
  return index_worker_detail::cgroup_parallelism_limit(
      static_cast<std::size_t>(CPU_COUNT(&affinity)), *memory, memberships,
      mountinfo);
#else
  return 1;
#endif
}

IndexWorker::IndexWorker(const std::filesystem::path &executable,
                         const std::filesystem::path &request,
                         const std::filesystem::path &result) {
  start(executable, request, result);
}

IndexWorker::~IndexWorker() { stop(); }

void IndexWorker::start(const std::filesystem::path &executable,
                        const std::filesystem::path &request,
                        const std::filesystem::path &result) {
  if (running())
    throw std::logic_error("index worker is already running");
  completed_.reset();
  std::string program = executable.string(), input = request.string(),
              output = result.string();
  char request_option[] = "--request", result_option[] = "--result";
  char *arguments[] = {program.data(), request_option, input.data(),
                       result_option,  output.data(),  nullptr};
  posix_spawnattr_t attributes;
  int error = posix_spawnattr_init(&attributes);
  if (error)
    throw std::system_error(error, std::generic_category(),
                            "initialize index worker");
  // A separate group allows cancellation to reap the entire worker subprocess.
  error = posix_spawnattr_setpgroup(&attributes, 0);
  if (!error)
    error = posix_spawnattr_setflags(&attributes, POSIX_SPAWN_SETPGROUP);
  posix_spawn_file_actions_t actions;
  const int actions_error = posix_spawn_file_actions_init(&actions);
  if (!error)
    error = actions_error;
  if (!error)
    error = posix_spawn_file_actions_addopen(&actions, STDIN_FILENO,
                                             "/dev/null", O_RDONLY, 0);
  if (!error)
    error = posix_spawn_file_actions_addopen(&actions, STDOUT_FILENO,
                                             "/dev/null", O_WRONLY, 0);
  // Diagnostics travel through the bounded result file, not the server log
  // pipe.
  if (!error)
    error = posix_spawn_file_actions_addopen(&actions, STDERR_FILENO,
                                             "/dev/null", O_WRONLY, 0);
  pid_t child = -1;
  if (!error)
    error = posix_spawn(&child, program.c_str(), &actions, &attributes,
                        arguments, environ);
  if (!actions_error)
    posix_spawn_file_actions_destroy(&actions);
  posix_spawnattr_destroy(&attributes);
  if (error)
    throw std::system_error(error, std::generic_category(),
                            "launch index worker");
  pid_ = child;
}

std::optional<int> IndexWorker::poll() {
  if (completed_) {
    const int status = *completed_;
    completed_.reset();
    return status;
  }
  if (!running())
    return std::nullopt;
  int status = 0;
  pid_t result;
  do {
    result = waitpid(pid_, &status, WNOHANG);
  } while (result < 0 && errno == EINTR);
  if (!result)
    return std::nullopt;
  if (result < 0)
    throw std::system_error(errno, std::generic_category(),
                            "poll index worker");
  pid_ = -1;
  return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
}

void IndexWorker::suspend() {
  if (!running())
    return;
  if (const auto status = poll()) {
    completed_ = status;
    return;
  }
  if (!kill(-pid_, SIGSTOP))
    return;
  const int signal_error = errno;
  const auto deadline =
      std::chrono::steady_clock::now() + kSignalFailureExitWindow;
  for (;;) {
    try {
      if (const auto status = poll()) {
        completed_ = status;
        return;
      }
    } catch (const std::system_error &) {
      // Preserve the signal failure when polling cannot establish completion.
      break;
    }
    if (std::chrono::steady_clock::now() >= deadline)
      break;
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
  }
  if (signal_error != ESRCH)
    throw std::system_error(signal_error, std::generic_category(),
                            "suspend index worker");
}

void IndexWorker::resume() {
  if (!running())
    return;
  if (const auto status = poll()) {
    completed_ = status;
    return;
  }
  if (!kill(-pid_, SIGCONT))
    return;
  const int signal_error = errno;
  const auto deadline =
      std::chrono::steady_clock::now() + kSignalFailureExitWindow;
  for (;;) {
    try {
      if (const auto status = poll()) {
        completed_ = status;
        return;
      }
    } catch (const std::system_error &) {
      // Preserve the signal failure when polling cannot establish completion.
      break;
    }
    if (std::chrono::steady_clock::now() >= deadline)
      break;
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
  }
  if (signal_error != ESRCH)
    throw std::system_error(signal_error, std::generic_category(),
                            "resume index worker");
}

void IndexWorker::stop() {
  if (!running())
    return;
  // SIGKILL is intentional: extraction has no shared state to unwind; the
  // parent commits only after a successful result and owns removal of staged
  // files.
  kill(-pid_, SIGKILL);
  int status = 0;
  while (waitpid(pid_, &status, 0) < 0 && errno == EINTR) {
  }
  pid_ = -1;
}

std::optional<std::uint64_t> IndexWorker::resident_bytes() const {
  if (!running())
    return std::nullopt;
#ifdef __APPLE__
  proc_taskinfo information{};
  if (proc_pidinfo(pid_, PROC_PIDTASKINFO, 0, &information,
                   sizeof(information)) != sizeof(information))
    return std::nullopt;
  return information.pti_resident_size;
#else
  std::ifstream input("/proc/" + std::to_string(pid_) + "/statm");
  std::uint64_t total = 0, resident = 0;
  if (!(input >> total >> resident))
    return std::nullopt;
  const auto page_size = sysconf(_SC_PAGESIZE);
  if (page_size <= 0)
    return std::nullopt;
  return resident * static_cast<std::uint64_t>(page_size);
#endif
}

std::filesystem::path current_executable_sibling(const char *name) {
#ifdef __APPLE__
  std::uint32_t size = 0;
  _NSGetExecutablePath(nullptr, &size);
  std::vector<char> path(size);
  if (_NSGetExecutablePath(path.data(), &size))
    throw std::runtime_error("cannot locate index worker executable");
  return std::filesystem::canonical(path.data()).parent_path() / name;
#else
  return std::filesystem::read_symlink("/proc/self/exe").parent_path() / name;
#endif
}

void lower_index_worker_priority() {
  if (setpriority(PRIO_PROCESS, 0, 15))
    throw std::system_error(errno, std::generic_category(),
                            "lower index worker priority");
  // Fail closed if budgets cannot be applied. A pathological TU must not occupy
  // an unbounded amount of CPU time or flood the staging filesystem.
  const rlimit cpu{120, 120};
  const rlimit output{128 * 1024 * 1024, 128 * 1024 * 1024};
  if (setrlimit(RLIMIT_CPU, &cpu) || setrlimit(RLIMIT_FSIZE, &output))
    throw std::system_error(errno, std::generic_category(),
                            "limit index worker resources");
#ifndef __APPLE__
  const rlimit memory{2ULL * 1024 * 1024 * 1024, 2ULL * 1024 * 1024 * 1024};
  if (setrlimit(RLIMIT_AS, &memory))
    throw std::system_error(errno, std::generic_category(),
                            "limit index worker memory");
#endif
}

void lower_index_thread_priority() {
#ifdef __APPLE__
  // Utility avoids background-class filesystem throttling while remaining
  // below the interactive threads serving user requests.
  pthread_set_qos_class_self_np(QOS_CLASS_UTILITY, 0);
#else
  const auto tid = static_cast<id_t>(syscall(SYS_gettid));
  if (tid > 0)
    setpriority(PRIO_PROCESS, tid, 10);
#endif
}

} // namespace ctk::platform
