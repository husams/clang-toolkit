#pragma once

#include "ctk/cache/snapshot.hpp"
#include "ctk/storage/store.hpp"
#include "native_temporary_artifact.hpp"
#include "snapshot/native_artifact_closure.hpp"
#include "snapshot/native_ast_writer.hpp"
#include <clang/Frontend/ASTUnit.h>
#include <llvm/ADT/StringRef.h>
#include <map>
#include <optional>

namespace ctk::clang_layer {
using DependencyBuffers = std::map<std::string, std::optional<llvm::StringRef>>;

struct AstSnapshotOwner final : ctk::cache::NativeSnapshotOwner {
  // Destruction preserves lazy artifact access until the AST is gone.
  std::unique_ptr<detail::NativeTemporaryArtifact> native_artifact;
  ctk::storage::SnapshotLeasePtr storage_lease;
  llvm::IntrusiveRefCntPtr<snapshot::CapturedFileSystem> filesystem;
  snapshot::NativeArtifactClosure artifact_closure;
  std::vector<std::pair<std::string, std::string>> environment;
  bool reusable = false;
  bool volatile_input = false;
  std::unique_ptr<snapshot::NativeAstWriter> writer;
  std::unique_ptr<clang::ASTUnit> unit;
  DependencyBuffers dependencies;
  bool storage_loaded = false;
  std::string storage_message;
};
} // namespace ctk::clang_layer
