#pragma once
#include "call_graph_budget.hpp"
#include <clang/Analysis/CallGraph.h>
#include <functional>
namespace ctk::clang_layer::calls {
class CallGraphBuilder final : public clang::CallGraph {
public:
  using ScopePredicate = std::function<bool(const clang::Decl *)>;
  explicit CallGraphBuilder(CallGraphBudget &budget,
                            bool main_file_only = false,
                            ScopePredicate scope = {},
                            bool defer_node_limit = false)
      : budget_(budget), main_file_only_(main_file_only),
        scope_(std::move(scope)), defer_node_limit_(defer_node_limit) {}
  bool TraverseDecl(clang::Decl *) override;

private:
  CallGraphBudget &budget_;
  bool main_file_only_;
  ScopePredicate scope_;
  bool defer_node_limit_;
};
} // namespace ctk::clang_layer::calls
