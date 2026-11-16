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
  // Directory insertions end in `/` before the closing delimiter.
  bool directory = false;
};

std::vector<PathSuggestion> path_suggestions(PathRole role, llvm::StringRef atom);

// Saved project names matching a project argument, quoted like paths.
std::vector<PathSuggestion> project_suggestions(llvm::StringRef atom,
                                                const std::vector<std::string> &names);

// True when the text before an argument puts it in an index command's project
// position: index status|pause|resume|cancel|rename "P", find/lookup ... in "P".
bool index_project_argument(llvm::StringRef before);

// Find the receiver of the final dot in the text before the completion word.
std::optional<llvm::StringRef> field_receiver(llvm::StringRef prefix);

// Resolve fields and indexes against the live session without executing CTK.
llvm::json::Array complete_fields(Values &values, llvm::StringRef reference,
                                  bool presence = false);

} // namespace ctk::jit
