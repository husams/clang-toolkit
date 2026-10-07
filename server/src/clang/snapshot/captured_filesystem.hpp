#pragma once
#include "captured_input.hpp"
#include "ctk/cache/snapshot.hpp"
#include "ctk/storage/store.hpp"
#include <map>
namespace ctk::clang_layer::snapshot {
class CapturedFileSystem final : public llvm::vfs::ProxyFileSystem {
public:
  explicit CapturedFileSystem(
      llvm::IntrusiveRefCntPtr<llvm::vfs::FileSystem> underlying);
  llvm::ErrorOr<llvm::vfs::Status> status(const llvm::Twine &) override;
  bool exists(const llvm::Twine &) override;
  llvm::ErrorOr<std::unique_ptr<llvm::vfs::File>>
  openFileForRead(const llvm::Twine &) override;
  llvm::ErrorOr<std::unique_ptr<llvm::vfs::File>>
  openFileForReadBinary(const llvm::Twine &path) override {
    return openFileForRead(path);
  }
  llvm::vfs::directory_iterator dir_begin(const llvm::Twine &,
                                          std::error_code &) override;
  std::error_code getRealPath(const llvm::Twine &,
                              llvm::SmallVectorImpl<char> &) override;
  // Add buffers consumed above the physical filesystem (main remap / native
  // reader).
  bool add_buffer(const std::string &path, llvm::StringRef bytes);
  bool validate() const;
  bool reusable() const { return complete_; }
  std::size_t estimated_bytes() const;
  void exclude_staged(const std::string &path) {
    inputs_.at(key(path)).staged = true;
  }
  void seal() { sealed_ = true; }
  const std::map<std::string, CapturedInput> &inputs() const { return inputs_; }
  static llvm::IntrusiveRefCntPtr<CapturedFileSystem> physical();
  static llvm::IntrusiveRefCntPtr<CapturedFileSystem>
  restore(const std::vector<ctk::storage::StoredInput> &inputs);

private:
  std::string key(const llvm::Twine &) const;
  std::string absolute_lookup(const llvm::Twine &) const;
  CapturedInput *capture(const llvm::Twine &);
  bool capture_entries(CapturedInput &input);
  std::map<std::string, CapturedInput> inputs_;
  bool sealed_ = false, complete_ = true;
  std::size_t bytes_ = 0;
  static constexpr std::size_t max_inputs = 16383,
                               max_bytes = 256 * 1024 * 1024;
};
} // namespace ctk::clang_layer::snapshot
