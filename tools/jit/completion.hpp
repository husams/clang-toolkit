#pragma once

#include <optional>
#include <string>
#include <vector>

#include <llvm/ADT/StringRef.h>
#include <llvm/Support/JSON.h>

namespace ctk::jit {

struct Values;
enum class PathRole;

struct PathSuggestion {
  std::string display;
  std::string insertion;
};

std::vector<PathSuggestion> path_suggestions(PathRole role, llvm::StringRef atom);

// Find the receiver of the final dot in the text before the completion word.
std::optional<llvm::StringRef> field_receiver(llvm::StringRef prefix);

// Resolve fields and indexes against the live session without executing CTK.
llvm::json::Array complete_fields(Values &values, llvm::StringRef reference,
                                  bool presence = false);

} // namespace ctk::jit
