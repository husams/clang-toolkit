#include "ctk/cache/snapshot.hpp"

#include "ctk/cache/compilation_context.hpp"
#include "ctk/cache/path_policy.hpp"

#include <stdexcept>
#include <utility>

namespace ctk::cache {
namespace {
std::string manifest(const std::string &profile,
                     const std::vector<InputObservation> &inputs) {
  std::string result = "ctk-manifest-v1:{\"inputs\":[";
  bool first = true;
  for (const auto &input : inputs) {
    if (!first)
      result += ',';
    first = false;
    if (path_key(input.path) != input.path)
      throw std::invalid_argument(
          "snapshot inputs must use canonical path keys");
    if (input.kind != InputKind::Absent && input.content_digest.empty())
      throw std::invalid_argument("consumed inputs require a content digest");
    if (input.kind != InputKind::File && input.validation_context.empty())
      throw std::invalid_argument(
          "lookup observations require validation context");
    const auto kind = input.kind == InputKind::File     ? "file"
                      : input.kind == InputKind::Absent ? "absent"
                                                        : "directory";
    result +=
        "{\"content_digest\":" + canonical_json_string(input.content_digest) +
        ",\"kind\":" + canonical_json_string(kind) +
        ",\"path\":" + canonical_json_string(input.path) +
        ",\"validation_context\":" +
        canonical_json_string(input.validation_context) + "}";
  }
  // Stat hints are deliberately excluded from generation identity.
  return result + "],\"profile\":" + canonical_json_string(profile) + "}";
}
} // namespace

SnapshotEntry::SnapshotEntry(std::uint64_t id, std::string identity,
                             LoadedSnapshot loaded)
    : generation(id), profile_identity(std::move(identity)),
      canonical_manifest(manifest(profile_identity, loaded.inputs)),
      inputs(std::move(loaded.inputs)), owner(std::move(loaded.owner)),
      estimated_bytes(loaded.estimated_bytes) {
  if (!owner || inputs.empty())
    throw std::invalid_argument(
        "snapshot requires native ownership and inputs");
}
} // namespace ctk::cache
