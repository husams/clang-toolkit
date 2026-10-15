#pragma once
#include "analysis/v1/variable_flow.pb.h"
#include <functional>
#include <string>
#include <vector>
namespace clang {
class ASTContext;
class VarDecl;
class Stmt;
class CFG;
} // namespace clang
namespace ctk::clang_layer::control_flow {
struct VariableRanges {
  std::vector<ctk::analysis::v1::VariableValueRange> before, after;
  std::string issue;
  std::uint64_t issue_usage{};
  bool overflow{};
};
VariableRanges
variable_ranges(clang::ASTContext &, const clang::VarDecl &, const clang::CFG &,
                const std::vector<ctk::analysis::v1::VariableUsage> &,
                const std::vector<const clang::Stmt *> &,
                const std::function<void()> &);
} // namespace ctk::clang_layer::control_flow
