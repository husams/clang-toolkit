#pragma once
#include "ctk/storage/store.hpp"
namespace ctk::clang_layer::snapshot {
struct NativeArtifact {
  ctk::storage::ArtifactKind kind;
  std::string path;
  std::string module_name;
  std::vector<std::size_t> dependencies;
};
} // namespace ctk::clang_layer::snapshot
