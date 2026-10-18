#pragma once

#include <cstdint>
#include <map>
#include <string>
#include <vector>

namespace ctk::clang_layer {
struct IndexedSymbol {
  std::string usr, name, qualified_name, kind, file_path, signature;
  std::uint32_t line = 0, column = 0;
  std::uint64_t byte_offset = 0;
  bool is_definition = false;
};
struct ProjectIndexExtraction {
  std::vector<IndexedSymbol> symbols;
  std::map<std::string, std::string> dependencies;
  std::string compile_context;
  std::uint64_t reused_header_symbols = 0;
};
struct ProjectIndexCommand {
  std::string source;
  std::string working_directory;
  std::vector<std::string> arguments;
  std::string serialized_context;
};
std::string
serialize_project_index_context(const std::string &working_directory,
                                const std::vector<std::string> &arguments,
                                const std::string &compiler = {});

// Runs an independent one-translation-unit Clang frontend using the selected
// compile database. No foreground AST, cache, or executor state is shared.
bool extract_project_index(
    const std::string &source, const std::string &compile_commands_directory,
    const std::string &working_directory,
    const std::vector<std::string> &arguments, ProjectIndexExtraction &result,
    std::string &error, const std::string &header_cache_directory = {},
    const std::map<std::string, std::string> *precomputed_include_inventories =
        nullptr);
bool list_project_translation_units(
    const std::string &compile_commands_directory,
    std::vector<ProjectIndexCommand> &translation_units, std::string &error);
} // namespace ctk::clang_layer
