#pragma once

#include "ctk/clang/tooling.hpp"

namespace ctk::clang_layer {
// Resolve the selected native command before AST cache identity is computed.
// Exact entries win; missing entries use Clang's TU command inference,
// including language/standard adjustment for headers. Explicit overrides append
// last. Without a usable command, automatic discovery preserves standalone
// defaults; an explicit database miss is an error.
FileInput resolve_compilation_command(const FileInput &input);
} // namespace ctk::clang_layer
