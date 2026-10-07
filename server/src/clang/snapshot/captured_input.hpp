#pragma once
#include <llvm/Support/VirtualFileSystem.h>
#include <memory>
#include <optional>
#include <string>
#include <vector>
namespace ctk::clang_layer::snapshot {
struct CapturedInput {
  bool staged = false;
  std::string path;
  std::string lookup_path;
  std::string real_path;
  std::vector<std::string> aliases;
  std::error_code error;
  llvm::vfs::Status status;
  std::shared_ptr<const std::string> bytes;
  std::optional<std::vector<llvm::vfs::directory_entry>> entries;
};
} // namespace ctk::clang_layer::snapshot
