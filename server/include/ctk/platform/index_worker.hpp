#pragma once

#include <cstdint>
#include <filesystem>
#include <optional>

namespace ctk::platform {

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
  void stop();
  bool running() const { return pid_ > 0; }

private:
  int pid_ = -1;
};

std::filesystem::path current_executable_sibling(const char *name);
// Called only inside the child, never on a foreground server thread.
void lower_index_worker_priority();

} // namespace ctk::platform
