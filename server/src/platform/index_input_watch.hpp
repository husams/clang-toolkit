#pragma once

#include <filesystem>
#include <memory>

namespace ctk::platform {
// Best-effort idle wake-up for registered project inputs. It uses OS change
// notifications and owns no descriptor per file. Call arm() after registering
// initial inputs and before reconciliation. Call arm() again after adding
// inputs to extend coverage; event history preserves edits during registration.
class IndexInputWatch {
public:
  IndexInputWatch();
  ~IndexInputWatch();
  IndexInputWatch(const IndexInputWatch &) = delete;
  IndexInputWatch &operator=(const IndexInputWatch &) = delete;

  bool add_file(const std::filesystem::path &file);
  bool add_directory(const std::filesystem::path &directory);
  bool arm();
  bool changed();
  void reset();

private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};
} // namespace ctk::platform
