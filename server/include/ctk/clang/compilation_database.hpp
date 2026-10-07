#pragma once

#include "ctk/clang/tooling.hpp"

namespace ctk::clang_layer {
// Resolve the selected native command before AST cache identity is computed.
// Explicit overrides append to its flags. No discovered command preserves the
// standalone-file defaults; an explicit database miss is an error.
FileInput resolve_compilation_command(const FileInput &input);
} // namespace ctk::clang_layer
