#pragma once

#include <functional>

#include <clang/ASTMatchers/ASTMatchFinder.h>

namespace ctk::clang_layer {

clang::ast_matchers::internal::DynTypedMatcher
scoped_matcher(const clang::DynTypedNode &root,
               const clang::ast_matchers::internal::DynTypedMatcher &query);

bool requires_translation_unit_match_metadata(llvm::StringRef query);

void match_subtree(const clang::DynTypedNode &root,
                   clang::ast_matchers::MatchFinder &finder,
                   clang::ASTContext &context,
                   const std::function<bool()> &should_continue);

} // namespace ctk::clang_layer
