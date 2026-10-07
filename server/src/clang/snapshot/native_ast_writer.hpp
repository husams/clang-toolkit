#pragma once
#include <clang/Basic/CodeGenOptions.h>
#include <clang/Basic/Version.h>
#include <clang/Serialization/ASTWriter.h>
#include <clang/Serialization/ModuleCache.h>
#include <llvm/Bitstream/BitstreamWriter.h>
namespace ctk::clang_layer::snapshot {
class NativeAstWriter final {
public:
  explicit NativeAstWriter(const clang::CodeGenOptions &options)
      : cache_(clang::createCrossProcessModuleCache()), options_(options),
        stream_(buffer_), writer_(stream_, buffer_, *cache_,
#if CLANG_VERSION_MAJOR >= 22
                                  options_,
#endif
                                  {}) {
  }
  std::size_t estimated_bytes() const {
    return sizeof(*this) + buffer_.capacity();
  }
  clang::ASTWriter &writer() { return writer_; }
  std::string serialize(clang::Sema &sema) {
    writer_.WriteAST(&sema, "", nullptr, "");
    return std::string(buffer_.begin(), buffer_.end());
  }

private:
  decltype(clang::createCrossProcessModuleCache()) cache_;
  clang::CodeGenOptions options_;
  llvm::SmallString<128> buffer_;
  llvm::BitstreamWriter stream_;
  clang::ASTWriter writer_;
};
} // namespace ctk::clang_layer::snapshot
