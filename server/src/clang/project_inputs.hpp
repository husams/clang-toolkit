#pragma once
#include "ctk/clang/tooling.hpp"
namespace ctk::clang_layer {
class ProjectInputs final {
public:
  explicit ProjectInputs(const Project &);
  const std::vector<FileInput> &files() const { return files_; }

private:
  std::vector<FileInput> files_;
};
} // namespace ctk::clang_layer
