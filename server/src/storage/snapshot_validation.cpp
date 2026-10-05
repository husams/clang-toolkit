#include "storage_internal.hpp"

#include <algorithm>
#include <functional>
#include <stdexcept>

namespace ctk::storage::detail {
namespace {

void validate_observation(const InputObservation &input) {
  validate_path(input.path);
  if (input.kind == ObservationKind::Content) {
    if (!input.digest_sha256 || !input.size_bytes || !input.mtime_ns)
      throw std::invalid_argument("content observations require digest, size and mtime");
    validate_sha256(*input.digest_sha256);
  } else if (input.kind == ObservationKind::Absent) {
    if (input.digest_sha256 || input.size_bytes || input.mtime_ns)
      throw std::invalid_argument("absent observations cannot carry content metadata");
    if (input.validation_context.empty())
      throw std::invalid_argument("absent observations require lookup context");
  } else {
    if (!input.digest_sha256 || input.size_bytes || !input.mtime_ns ||
        input.validation_context.empty())
      throw std::invalid_argument("directory observations require namespace metadata");
    validate_sha256(*input.digest_sha256);
  }
}

void validate_closure(const std::vector<ArtifactKind> &kinds,
                      const std::vector<ArtifactDependency> &edges) {
  if (kinds.empty())
    throw std::invalid_argument("artifact closure is empty");
  std::optional<std::size_t> root;
  for (std::size_t index = 0; index < kinds.size(); ++index) {
    if (kinds[index] == ArtifactKind::TranslationUnit) {
      if (root) throw std::invalid_argument("artifact closure has multiple TU roots");
      root = index;
    }
  }
  if (!root) throw std::invalid_argument("artifact closure lacks a TU root");

  std::vector<std::vector<std::size_t>> children(kinds.size());
  for (const auto &edge : edges) {
    if (edge.parent_index >= kinds.size() || edge.dependency_index >= kinds.size() ||
        edge.parent_index == edge.dependency_index)
      throw std::invalid_argument("artifact dependency index is invalid");
    auto &siblings = children[edge.parent_index];
    if (std::ranges::find(siblings, edge.dependency_index) != siblings.end())
      throw std::invalid_argument("duplicate artifact dependency");
    siblings.push_back(edge.dependency_index);
  }
  std::vector<unsigned char> state(kinds.size(), 0);
  std::size_t visited = 0;
  std::function<void(std::size_t)> visit = [&](std::size_t node) {
    if (state[node] == 1) throw std::invalid_argument("artifact closure contains a cycle");
    if (state[node] == 2) return;
    state[node] = 1;
    for (const auto child : children[node]) visit(child);
    state[node] = 2;
    ++visited;
  };
  visit(*root);
  if (visited != kinds.size())
    throw std::invalid_argument("artifact closure has an unreachable artifact");
}

} // namespace

void validate_snapshot_draft(const SnapshotDraft &snapshot,
                              std::uint64_t maximum_artifact_size) {
  validate_path(snapshot.profile.main_path);
  validate_path(snapshot.profile.working_directory);
  if (!snapshot.profile.reusable)
    throw std::invalid_argument("non-reusable compilation profile cannot be persisted");
  (void)canonical_toolchain(snapshot.profile.toolchain);
  (void)canonical_profile(snapshot.profile);
  if (snapshot.profile.input_spelling.empty())
    throw std::invalid_argument("compiler input spelling is required");

  std::size_t main_sources = 0;
  for (const auto &input : snapshot.inputs) {
    validate_observation(input);
    if (input.role == InputRole::MainSource) {
      ++main_sources;
      if (input.path != snapshot.profile.main_path ||
          input.kind != ObservationKind::Content)
        throw std::invalid_argument("main-source observation does not match profile");
    }
  }
  if (snapshot.inputs.empty() || main_sources != 1)
    throw std::invalid_argument("snapshot requires one main-source observation");

  std::vector<ArtifactKind> kinds;
  kinds.reserve(snapshot.artifacts.size());
  std::vector<std::string> logical_paths;
  for (const auto &artifact : snapshot.artifacts) {
    validate_path(artifact.logical_path);
    if (artifact.native_bytes.size() > maximum_artifact_size)
      throw std::invalid_argument("native artifact exceeds configured size limit");
    kinds.push_back(artifact.kind);
    logical_paths.push_back(artifact.logical_path);
  }
  std::ranges::sort(logical_paths);
  if (std::adjacent_find(logical_paths.begin(), logical_paths.end()) != logical_paths.end())
    throw std::invalid_argument("artifact logical paths must be unique");
  validate_closure(kinds, snapshot.dependencies);
}

void validate_stored_closure(const SnapshotDescriptor &snapshot) {
  std::vector<ArtifactKind> kinds;
  for (const auto &artifact : snapshot.artifacts)
    kinds.push_back(artifact.kind);
  validate_closure(kinds, snapshot.dependencies);
}

} // namespace ctk::storage::detail
