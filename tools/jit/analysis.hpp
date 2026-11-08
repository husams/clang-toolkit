#pragma once

#include "ctk/cache/snapshot.hpp"
#include "values.hpp"

#include <optional>

#include <llvm/ADT/StringRef.h>

namespace clang {
class ASTUnit;
}

namespace ctk::jit {

AstHandle retain_snapshot(ctk::cache::SnapshotPtr snapshot);
AstHandle retain_ast(std::unique_ptr<clang::ASTUnit> unit, std::uint64_t generation);

const Value* analyze(Values& runtime, llvm::StringRef operation, const AstHandle& ast,
                     const NativeNode* selected, const Value* operand, llvm::StringRef options,
                     bool display);

const Value* navigate(Values& runtime, const NativeNode& selected, const MatcherValue* matcher,
                      llvm::StringRef axis, std::uint64_t maximum,
                      std::optional<std::uint64_t> index, bool step, bool display,
                      bool bind_candidate = true);

} // namespace ctk::jit
