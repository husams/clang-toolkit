#pragma once
#include "call_graph_budget.hpp"
#include <clang/Analysis/CallGraph.h>
namespace ctk::clang_layer::calls {
class CallGraphBuilder final : public clang::CallGraph {
public:
  explicit CallGraphBuilder(CallGraphBudget &budget, bool main_file_only = false)
      : budget_(budget), main_file_only_(main_file_only) {}
  bool TraverseDecl(clang::Decl *) override;

private:
  CallGraphBudget &budget_;
  bool main_file_only_;
};
} // namespace ctk::clang_layer::calls
