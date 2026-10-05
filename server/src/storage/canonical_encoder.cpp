#include "storage_internal.hpp"

#include "ctk/cache/compilation_context.hpp"

#include <stdexcept>

namespace ctk::storage::detail {
namespace {

std::string quote(std::string_view value) {
  return ctk::cache::canonical_json_string(value);
}

std::string_view role_name(InputRole role) {
  switch (role) {
  case InputRole::MainSource: return "MAIN_SOURCE";
  case InputRole::Header: return "HEADER";
  case InputRole::Response: return "RESPONSE";
  case InputRole::PchInput: return "PCH_INPUT";
  case InputRole::ModuleInput: return "MODULE_INPUT";
  case InputRole::VfsOverlay: return "VFS_OVERLAY";
  case InputRole::Lookup: return "LOOKUP";
  }
  throw std::invalid_argument("unknown input role");
}

std::string_view observation_name(ObservationKind kind) {
  switch (kind) {
  case ObservationKind::Content: return "CONTENT";
  case ObservationKind::Absent: return "ABSENT";
  case ObservationKind::Directory: return "DIRECTORY";
  }
  throw std::invalid_argument("unknown observation kind");
}

std::string_view artifact_name(ArtifactKind kind) {
  switch (kind) {
  case ArtifactKind::TranslationUnit: return "TRANSLATION_UNIT";
  case ArtifactKind::Pch: return "PCH";
  case ArtifactKind::Module: return "MODULE";
  }
  throw std::invalid_argument("unknown artifact kind");
}

std::string optional_json(const std::optional<std::string> &value) {
  return value ? quote(*value) : "null";
}

std::string optional_json(const std::optional<std::uint64_t> &value) {
  return value ? std::to_string(*value) : "null";
}

} // namespace

Bytes canonical_toolchain(const ToolchainIdentity &toolchain) {
  if (toolchain.clang_version.empty() || toolchain.build_identity.empty() ||
      toolchain.target_triple.empty() || toolchain.resource_directory.empty() ||
      toolchain.resource_content_identity.empty())
    throw std::invalid_argument("toolchain compatibility identity is incomplete");
  return "ctk-toolchain-v1:{\"build_identity\":" + quote(toolchain.build_identity) +
         ",\"clang_version\":" + quote(toolchain.clang_version) +
         ",\"resource_content_identity\":" +
         quote(toolchain.resource_content_identity) +
         ",\"resource_directory\":" + quote(toolchain.resource_directory) +
         ",\"target_triple\":" + quote(toolchain.target_triple) + "}";
}

Bytes canonical_profile(const CompilationProfile &profile) {
  ctk::cache::CompilationContext context;
  context.schema_version = profile.schema_version;
  context.input_spelling = profile.input_spelling;
  context.working_directory = profile.working_directory;
  context.toolchain_identity = profile.toolchain.build_identity;
  context.resource_directory = profile.toolchain.resource_directory;
  context.target = profile.toolchain.target_triple;
  context.sysroot = profile.sysroot;
  context.arguments = profile.arguments;
  context.environment = profile.environment;
  context.vfs_overlays = profile.vfs_overlays;
  context.reusable = profile.reusable;
  return context.canonical_bytes();
}

Bytes canonical_manifest(const SnapshotDraft &snapshot) {
  std::string output = "ctk-manifest-v1:{\"artifacts\":[";
  for (std::size_t index = 0; index < snapshot.artifacts.size(); ++index) {
    if (index != 0) output.push_back(',');
    const auto &artifact = snapshot.artifacts[index];
    output += "{\"kind\":" + quote(artifact_name(artifact.kind)) +
              ",\"logical_path\":" + quote(artifact.logical_path) + "}";
  }
  output += "],\"dependencies\":[";
  for (std::size_t index = 0; index < snapshot.dependencies.size(); ++index) {
    if (index != 0) output.push_back(',');
    const auto &edge = snapshot.dependencies[index];
    output += "{\"dependency_index\":" +
              std::to_string(edge.dependency_index) +
              ",\"parent_index\":" + std::to_string(edge.parent_index) + "}";
  }
  output += "],\"inputs\":[";
  for (std::size_t index = 0; index < snapshot.inputs.size(); ++index) {
    if (index != 0) output.push_back(',');
    const auto &input = snapshot.inputs[index];
    output += "{\"digest_sha256\":" + optional_json(input.digest_sha256) +
              ",\"kind\":" + quote(observation_name(input.kind)) +
              ",\"path\":" + quote(input.path) +
              ",\"role\":" + quote(role_name(input.role)) +
              ",\"size_bytes\":" + optional_json(input.size_bytes) +
              ",\"validation_context\":" + quote(input.validation_context) + "}";
  }
  output += "],\"profile\":" + quote(canonical_profile(snapshot.profile)) + "}";
  return output;
}

} // namespace ctk::storage::detail
