#pragma once
#include "call_graph_budget.hpp"
#include <clang/AST/RecursiveASTVisitor.h>
#include <unordered_map>
namespace ctk::clang_layer::calls {
class DeclarationOrder final
    : public clang::RecursiveASTVisitor<DeclarationOrder> {
public:
  explicit DeclarationOrder(CallGraphBudget &budget) : budget_(budget) {}
  bool shouldVisitImplicitCode() const { return true; }
  bool shouldVisitTemplateInstantiations() const { return true; }
  bool VisitDecl(clang::Decl *);
  std::unordered_map<const clang::Decl *, std::size_t> ordinals;

private:
  CallGraphBudget &budget_;
};
} // namespace ctk::clang_layer::calls
