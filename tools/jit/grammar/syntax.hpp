#pragma once

#include <string>
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

enum class PathRole { None, File, Directory, Relative };
PathRole path_role_after(llvm::StringRef prefix);

/// Decode escapes in a quoted string. Interpolation is handled by the caller.
std::string decode_ctk_string(std::string_view literal);

} // namespace ctk::jit
