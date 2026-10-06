#pragma once

#include "ctk/platform/temporary_directory.hpp"

#include <filesystem>
#include <string_view>

namespace ctk::clang_layer::detail {

class NativeTemporaryArtifact final {
public:
  explicit NativeTemporaryArtifact(std::string_view prefix)
      : directory_(prefix), artifact_path_(directory_.path() / "artifact.ast") {
  }

  const std::filesystem::path &path() const noexcept { return artifact_path_; }

private:
  ctk::platform::TemporaryDirectory directory_;
  std::filesystem::path artifact_path_;
};

} // namespace ctk::clang_layer::detail
