#pragma once
#include "cfg_budget.hpp"
#include <clang/AST/RecursiveASTVisitor.h>
#include <unordered_set>
namespace ctk::clang_layer::control_flow {
class CfgFunctionCollector final
    : public clang::RecursiveASTVisitor<CfgFunctionCollector> {
public:
  CfgFunctionCollector(std::string name, CfgBudget &budget)
      : name_(std::move(name)), budget_(budget) {}
  bool shouldVisitImplicitCode() const { return true; }
  bool shouldVisitTemplateInstantiations() const { return true; }
  bool VisitFunctionDecl(clang::FunctionDecl *);
  std::vector<clang::FunctionDecl *> definitions;
  bool dependent = false;

private:
  std::string name_;
  CfgBudget &budget_;
  std::unordered_set<clang::FunctionDecl *> seen_;
};
} // namespace ctk::clang_layer::control_flow
