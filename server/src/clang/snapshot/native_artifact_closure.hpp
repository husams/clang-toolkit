#pragma once
#include "captured_filesystem.hpp"
#include "native_artifact.hpp"
#include <clang/Frontend/ASTUnit.h>
namespace ctk::clang_layer::snapshot {
struct NativeArtifactClosure {
  std::vector<NativeArtifact> artifacts;
  bool reusable = true;
};
NativeArtifactClosure
capture_native_artifacts(clang::ASTUnit &, CapturedFileSystem &,
                         const std::string &working_directory);
} // namespace ctk::clang_layer::snapshot
