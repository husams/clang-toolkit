#pragma once

#include "ctk/platform/directory_watch.hpp"
#include "project_index_store.hpp"

namespace ctk::net::index_detail {
// Digest-only, bounded, and confined to the index thread. Kernel directory
// events guard reuse; neither timestamps nor a TTL decide freshness. Header
// contents remain independently hashed before every publication.
class IncludeInventoryCache {
public:
  std::string digest(const fs::path &root,
                     const std::function<bool()> &allowed = {}) {
    for (unsigned retry = 0; retry != 3; ++retry) {
      if (watch_.changed())
        invalidate();
      const auto before = platform::DirectoryWatch::identity(root);
      auto found = entries_.find(root);
      if (before && found != entries_.end() &&
          found->second.identity == *before)
        return found->second.digest;
      bool monitored = true;
      const auto inventory = cache::include_inventory(
          root, allowed, [&](const fs::path &directory) {
            monitored = watch_.add(directory) && monitored;
          });
      const auto value = digest_text(inventory);
      const auto after = platform::DirectoryWatch::identity(root);
      if (watch_.changed() || before != after) {
        invalidate();
        continue;
      }
      if (before && monitored) {
        if (entries_.size() >= 128)
          invalidate();
        else
          entries_.insert_or_assign(root, Entry{*before, value});
      }
      return value;
    }
    // A changing tree cannot validate the old extracted inputs. The caller
    // retries the TU rather than publishing an unguarded cached digest.
    return {};
  }

private:
  void invalidate() {
    entries_.clear();
    watch_.reset();
  }
  struct Entry {
    platform::DirectoryWatch::Identity identity;
    std::string digest;
  };
  platform::DirectoryWatch watch_;
  std::map<fs::path, Entry> entries_;
};
} // namespace ctk::net::index_detail
