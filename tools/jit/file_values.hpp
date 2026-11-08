#pragma once

#include <llvm/Support/Error.h>

#include "values.hpp"

namespace ctk::jit {

struct FileEntry {
  std::string path;
  std::string absolute;
  std::string modified;
  std::int64_t size = 0;
  bool directory = false;
};

const std::string* file_path(const Value& value, bool allow_directory = false);
std::optional<Value> file_field(const FileEntry& entry, llvm::StringRef name);
Value file_record(const FileEntry& entry);
llvm::Expected<std::optional<std::vector<std::string>>> match_paths(llvm::StringRef path);

extern "C" const Value* ctk_jit_glob_v1(Values* runtime, const Value* pattern);

} // namespace ctk::jit
