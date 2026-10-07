#pragma once

#include "ctk/cache/snapshot.hpp"
#include "ctk/storage/store.hpp"
#include "native_temporary_artifact.hpp"
#include <clang/Frontend/ASTUnit.h>
#include <llvm/ADT/StringRef.h>
#include <map>
#include <optional>

namespace ctk::clang_layer {
using DependencyBuffers = std::map<std::string, std::optional<llvm::StringRef>>;

struct AstSnapshotOwner final : ctk::cache::NativeSnapshotOwner {
  // Destroy the AST and lease before removing the directory that may still be
  // consulted by lazy AST accessors.
  std::unique_ptr<detail::NativeTemporaryArtifact> native_artifact;
  ctk::storage::SnapshotLeasePtr storage_lease;
  std::unique_ptr<clang::ASTUnit> unit;
  DependencyBuffers dependencies;
  bool storage_loaded = false;
  std::string storage_message;
};
} // namespace ctk::clang_layer
