#pragma once

#include "ctk/clang/tooling.hpp"

#include <string>

namespace ctk::clang_layer {
// The single compilation-database resolver shared by the server and ctk-jit.
//
// Database selection: an explicit input.compilation_database (a JSON file,
// a compile_flags.txt, or a directory holding either) wins; a missing explicit
// path is an error. Otherwise discovery checks the working directory and its
// ancestors, then the source directory and its ancestors; at each level it
// tries compile_commands.json, build/, build/dev/, build/release/ and finally
// compile_flags.txt.
//
// Command selection: exact entries win (the first in database order when a
// file has several); missing entries first use the first TU in the same
// source directory (database order), then Clang's general TU command
// inference, including language/standard adjustment for headers. Explicit
// overrides append last. Without a usable command, automatic discovery
// preserves standalone defaults; an explicit database miss is an error.
//
// The result's driver is the database's compiler (after ccache-style
// launchers) and is removed from compile_arguments; target and driver mode
// implied by its name are kept as arguments. compilation_source records
// whether the command came from an explicit or a discovered database.
FileInput resolve_compilation_command(const FileInput &input);
// True for GCC drivers (gcc, g++, versioned or target-prefixed names, and
// cc/c++ aliases that resolve to them). Apple's /usr/bin shims are Clang.
bool is_gcc_driver(const std::string &driver);
// An empty input path borrows the first JSON database entry in source order.
// An explicit path uses the same exact/inferred command rules as file parsing.
FileInput resolve_snippet_compilation_command(const FileInput &input);
// Apply Clang's language/standard transfer before appending snippet overrides.
// The donor path is retained for relative include lookup.
FileInput
transfer_snippet_compilation_command(FileInput donor,
                                     const std::vector<std::string> &overrides);
} // namespace ctk::clang_layer
