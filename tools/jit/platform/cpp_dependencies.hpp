#pragma once

#include <chrono>
#include <filesystem>
#include <optional>

#include <llvm/ADT/StringRef.h>
#include <llvm/Support/Error.h>
#include <llvm/Support/JSON.h>

namespace ctk::jit {

llvm::Expected<llvm::json::Value> dependency_stamp(const std::filesystem::path &path);

std::optional<llvm::json::Object> observe_cpp_dependencies(
    llvm::StringRef depfile, llvm::StringRef diagnostics,
    std::chrono::system_clock::time_point started);

bool cpp_dependencies_unchanged(const llvm::json::Object &observed);

} // namespace ctk::jit
