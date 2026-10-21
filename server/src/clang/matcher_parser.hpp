#pragma once

#include <clang/ASTMatchers/Dynamic/Diagnostics.h>
#include <clang/ASTMatchers/Dynamic/VariantValue.h>
#include <llvm/ADT/StringRef.h>
#include <optional>

namespace ctk::clang_layer {

// Preserve Clang's matcher semantics and supply diagnostics for silent failures.
std::optional<clang::ast_matchers::internal::DynTypedMatcher>
parse_matcher_expression(
    llvm::StringRef &text,
    clang::ast_matchers::dynamic::Diagnostics &diagnostics);

} // namespace ctk::clang_layer
