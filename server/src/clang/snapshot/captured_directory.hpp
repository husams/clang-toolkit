#pragma once
#include <llvm/Support/VirtualFileSystem.h>
#include <vector>
namespace ctk::clang_layer::snapshot {
class CapturedDirectory final : public llvm::vfs::detail::DirIterImpl {
public:
  explicit CapturedDirectory(std::vector<llvm::vfs::directory_entry> entries)
      : entries_(std::move(entries)) {
    if (!entries_.empty())
      CurrentEntry = entries_[0];
  }
  std::error_code increment() override {
    ++index_;
    CurrentEntry = index_ < entries_.size() ? entries_[index_]
                                            : llvm::vfs::directory_entry{};
    return {};
  }

private:
  std::vector<llvm::vfs::directory_entry> entries_;
  std::size_t index_ = 0;
};
} // namespace ctk::clang_layer::snapshot
