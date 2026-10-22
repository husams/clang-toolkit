#pragma once

#include "ctk/clang/tooling.hpp"

namespace ctk::clang_layer {
// Resolve the selected native command before AST cache identity is computed.
// Exact entries win; missing entries first use the first TU in the same source
// directory (database order), then Clang's general TU command inference,
// including language/standard adjustment for headers. Explicit overrides append
// last. Without a usable command, automatic discovery preserves standalone
// defaults; an explicit database miss is an error.
FileInput resolve_compilation_command(const FileInput &input);
// An empty input path borrows the first JSON database entry in source order.
// An explicit path uses the same exact/inferred command rules as file parsing.
FileInput resolve_snippet_compilation_command(const FileInput &input);
// Apply Clang's language/standard transfer before appending snippet overrides.
// The donor path is retained for relative include lookup.
FileInput
transfer_snippet_compilation_command(FileInput donor,
                                     const std::vector<std::string> &overrides);
} // namespace ctk::clang_layer
