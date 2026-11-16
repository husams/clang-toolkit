#pragma once

#include <string>
#include <vector>

#include <llvm/ADT/StringRef.h>

namespace ctk::jit {

struct NativeHelp {
  std::string text;
  std::string markdown;
};

NativeHelp native_help(llvm::StringRef topic);
std::vector<std::string> native_help_topics(llvm::StringRef prefix);
// Literal second words from a command's usage lines, such as index start.
std::vector<std::string> native_subcommands(llvm::StringRef command);
bool editor_keyword(llvm::StringRef word);
llvm::StringRef editor_matcher_kind(llvm::StringRef word);

} // namespace ctk::jit
