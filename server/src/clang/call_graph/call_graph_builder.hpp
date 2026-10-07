#pragma once
#include "call_graph_budget.hpp"
#include <clang/Analysis/CallGraph.h>
namespace ctk::clang_layer::calls {
class CallGraphBuilder final : public clang::CallGraph {
public:
  explicit CallGraphBuilder(CallGraphBudget &budget) : budget_(budget) {}
  bool TraverseDecl(clang::Decl *) override;

private:
  CallGraphBudget &budget_;
};
} // namespace ctk::clang_layer::calls
