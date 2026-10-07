#pragma once
#include "captured_input.hpp"
#include <llvm/Support/MemoryBuffer.h>
namespace ctk::clang_layer::snapshot {
class CapturedFile final : public llvm::vfs::File {
public:
  explicit CapturedFile(CapturedInput input) : input_(std::move(input)) {}
  llvm::ErrorOr<llvm::vfs::Status> status() override { return input_.status; }
  llvm::ErrorOr<std::unique_ptr<llvm::MemoryBuffer>>
  getBuffer(const llvm::Twine &name, int64_t = -1, bool requires_null = true,
            bool = false) override {
    return llvm::MemoryBuffer::getMemBuffer(*input_.bytes, name.str(),
                                            requires_null);
  }
  std::error_code close() override { return {}; }

private:
  CapturedInput input_;
};
} // namespace ctk::clang_layer::snapshot
