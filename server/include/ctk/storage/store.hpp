#pragma once

#include <optional>
#include <string>

namespace ctk::storage {

// Persistent cache backend (filesystem blobs + SQLite index).
class Store {
 public:
  virtual ~Store() = default;
  virtual std::optional<std::string> load(const std::string& key) = 0;
  virtual void save(const std::string& key, const std::string& value) = 0;
};

}  // namespace ctk::storage
