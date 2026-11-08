#pragma once

#include <string_view>
#include <vector>

#include <llvm/ADT/StringRef.h>
#include <llvm/Support/Error.h>

namespace ctk::jit {

/// Byte offsets in the submitted UTF-8 text. The source must outlive the tree.
struct Syntax {
  std::string_view name;
  std::string_view text;
  std::size_t begin = 0;
  std::size_t end = 0;
  std::vector<Syntax> children;
};

llvm::Expected<Syntax> parse_ctk(llvm::StringRef source);

} // namespace ctk::jit
