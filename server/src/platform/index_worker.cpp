#include "ctk/platform/index_worker.hpp"

#include <cerrno>
#include <csignal>
#include <fcntl.h>
#include <fstream>
#include <spawn.h>
#include <stdexcept>
#include <string>
#include <sys/resource.h>
#include <sys/wait.h>
#include <system_error>
#include <unistd.h>
#include <vector>

#ifdef __APPLE__
#include <libproc.h>
#include <mach-o/dyld.h>
#include <pthread.h>
#else
#include <sys/syscall.h>
#endif

extern char **environ;

namespace ctk::platform {

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
  if (running() && kill(-pid_, SIGSTOP) && errno != ESRCH)
    throw std::system_error(errno, std::generic_category(),
                            "suspend index worker");
}

void IndexWorker::resume() {
  if (running() && kill(-pid_, SIGCONT) && errno != ESRCH)
    throw std::system_error(errno, std::generic_category(),
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
