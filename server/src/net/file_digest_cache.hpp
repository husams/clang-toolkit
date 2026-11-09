#pragma once

#include "ctk/platform/index_file_reader.hpp"
#include "project_index_store.hpp"

#include <algorithm>
#include <array>
#include <cstddef>
#include <filesystem>
#include <functional>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>

namespace ctk::net::index_detail {
// The index thread retains a bounded set of open file descriptors to avoid
// repeated open/close. It always reads and hashes the current file contents.
class FileDigestCache {
public:
  static constexpr std::size_t max_capacity = 2048;
  using Allowed = std::function<bool()>;
  struct Counters {
    std::uint64_t hits = 0;
    std::uint64_t hashes = 0;
    std::uint64_t cached = 0;
    std::uint64_t uncached = 0;
    std::uint64_t invalidations = 0;
  };

  explicit FileDigestCache(std::size_t capacity = max_capacity)
      : capacity_(platform::IndexFileReader::descriptor_budget(
            std::min(capacity, max_capacity))) {}

  std::string digest(const std::string &path, const Allowed &allowed = {}) {
    if (allowed && !allowed())
      return {};
    if (path.starts_with("@include-tree:")) {
      ++counters_.hashes;
      const auto value = digest_file(path, allowed);
      return (!allowed || allowed()) ? value : std::string{};
    }
    std::error_code path_error;
    const auto absolute = std::filesystem::absolute(path, path_error);
    if (path_error)
      return uncached_digest(path, allowed);
    const auto key = absolute.lexically_normal();

    auto found = entries_.find(key);
    std::optional<platform::IndexFileIdentity> path_before;
    if (found != entries_.end()) {
      path_before = platform::IndexFileReader::path_identity(key);
      if (!path_before || found->second.identity != *path_before) {
        entries_.erase(found);
        ++counters_.invalidations;
        found = entries_.end();
      }
    }
    if (found != entries_.end())
      ++counters_.hits;

    if (found == entries_.end()) {
      if (entries_.size() >= capacity_)
        return uncached_digest(key.string(), allowed);
      auto reader = std::make_unique<platform::IndexFileReader>(key);
      if (!reader->valid() || !reader->cacheable())
        return uncached_digest(key.string(), allowed);
      const auto opened = reader->identity();
      path_before = platform::IndexFileReader::path_identity(key);
      if (!opened || !path_before || *opened != *path_before)
        return uncached_digest(key.string(), allowed);
      found = entries_.emplace(key, Entry{std::move(reader), *opened}).first;
      ++counters_.cached;
    }

    ++counters_.hashes;
    if (!path_before || found->second.identity != *path_before) {
      entries_.erase(found);
      ++counters_.invalidations;
      return {};
    }

    const auto value = hash_current(*found->second.reader, allowed);
    if (value.empty() || (allowed && !allowed()))
      return {};

    const auto path_after = platform::IndexFileReader::path_identity(key);
    if (!path_after || *path_before != *path_after ||
        found->second.identity != *path_after) {
      entries_.erase(found);
      ++counters_.invalidations;
      return {};
    }
    return value;
  }

  const Counters &counters() const { return counters_; }
  std::size_t size() const { return entries_.size(); }

private:
  struct Entry {
    std::unique_ptr<platform::IndexFileReader> reader;
    platform::IndexFileIdentity identity;
  };

  static std::string hash_current(const platform::IndexFileReader &reader,
                                  const Allowed &allowed) {
    std::unique_ptr<EVP_MD_CTX, decltype(&EVP_MD_CTX_free)> context(
        EVP_MD_CTX_new(), EVP_MD_CTX_free);
    if (!context || !EVP_DigestInit_ex(context.get(), EVP_sha256(), nullptr))
      throw std::runtime_error("cannot hash index dependency");

    std::array<unsigned char, 65536> buffer;
    std::uint64_t offset = 0;
    for (;;) {
      if (allowed && !allowed())
        return {};
      const auto count = reader.read_at(buffer.data(), buffer.size(), offset);
      if (count < 0)
        return {};
      if (count == 0)
        break;
      if (!EVP_DigestUpdate(context.get(), buffer.data(),
                            static_cast<std::size_t>(count)))
        throw std::runtime_error("cannot hash index dependency");
      offset += static_cast<std::uint64_t>(count);
    }

    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned count = 0;
    if (!EVP_DigestFinal_ex(context.get(), digest, &count))
      throw std::runtime_error("cannot finalize dependency digest");
    return hex(digest, count);
  }

  std::string uncached_digest(const std::string &path, const Allowed &allowed) {
    ++counters_.uncached;
    ++counters_.hashes;
    const auto value = digest_file(path, allowed);
    return (!allowed || allowed()) ? value : std::string{};
  }

  std::size_t capacity_;
  std::map<std::filesystem::path, Entry> entries_;
  Counters counters_;
};
} // namespace ctk::net::index_detail
