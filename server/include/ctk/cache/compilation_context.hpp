#pragma once

#include <cstdint>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace ctk::cache {

// Stable, versioned compilation identity. The digest is only a lookup aid;
// callers must compare canonical_bytes() after a digest hit.
struct CompilationContext {
  std::uint32_t schema_version = 1;
  std::string input_spelling;
  std::string working_directory;
  std::string toolchain_identity;
  std::string resource_directory;
  std::string target;
  std::string sysroot;
  std::vector<std::string> arguments;
  std::vector<std::pair<std::string, std::string>> environment;
  std::vector<std::string> vfs_overlays;
  bool reusable = true;

  // Deterministic UTF-8 JSON with fixed sorted keys and no path/Unicode
  // normalization. Throws std::invalid_argument for invalid identities.
  std::string canonical_bytes() const;
  std::string digest() const;
};

// Deterministic non-cryptographic digest for indexing canonical bytes.
std::string compilation_digest(std::string_view canonical_bytes);

// JSON string literal shared by versioned identity and snapshot manifests.
std::string canonical_json_string(std::string_view value);

} // namespace ctk::cache
