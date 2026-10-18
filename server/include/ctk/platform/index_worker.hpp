#pragma once

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <string_view>

namespace ctk::platform {

// Conservative process-wide concurrency budget for translation-unit extraction.
std::size_t index_worker_parallelism_limit();

namespace index_worker_detail {
// Exposed for deterministic policy tests; production code should use the probe
// above.
std::size_t parallelism_limit(std::size_t logical_cpus,
                              std::uint64_t physical_memory_bytes);
std::optional<std::uint64_t> parse_memory_limit(std::string_view value);
std::optional<std::size_t> parse_cpu_quota(std::string_view value);
std::string cgroup_limit_line(std::string_view contents);
bool missing_cgroup_limit_is_unlimited(bool unified, bool mount_root);
std::size_t cgroup_parallelism_limit(std::size_t host_cpus,
                                     std::uint64_t host_memory,
                                     std::string_view memberships,
                                     std::string_view mountinfo);
} // namespace index_worker_detail

// Owns one isolated extractor process; poll and stop always reap the child.
class IndexWorker {
public:
  IndexWorker() = default;
  IndexWorker(const std::filesystem::path &executable,
              const std::filesystem::path &request,
              const std::filesystem::path &result);
  ~IndexWorker();
  IndexWorker(const IndexWorker &) = delete;
  IndexWorker &operator=(const IndexWorker &) = delete;
  void start(const std::filesystem::path &executable,
             const std::filesystem::path &request,
             const std::filesystem::path &result);
  std::optional<int> poll();
  std::optional<std::uint64_t> resident_bytes() const;
  // Stop CPU and I/O while foreground work runs, retaining extraction state.
  void suspend();
  void resume();
  void stop();
  bool running() const { return pid_ > 0; }

private:
  int pid_ = -1;
  std::optional<int> completed_;
};

std::filesystem::path current_executable_sibling(const char *name);
// Called only inside the child, never on a foreground server thread.
void lower_index_worker_priority();
// Lower only the index controller thread, leaving foreground RPC threads alone.
void lower_index_thread_priority();

} // namespace ctk::platform
