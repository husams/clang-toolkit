#include "cfg_function_collector.hpp"
namespace ctk::clang_layer::control_flow {
bool CfgFunctionCollector::VisitFunctionDecl(clang::FunctionDecl *function) {
  budget_.check();
  if (function->getQualifiedNameAsString() != name_ ||
      !function->doesThisDeclarationHaveABody())
    return true;
  if (function->isDependentContext()) {
    dependent = true;
    return true;
  }
  if (!seen_.insert(function->getCanonicalDecl()).second)
    return true;
  if (definitions.size() == budget_.limits.max_functions)
    throw BuildFailure(MatchCode::ResourceExhausted,
                       "CFG function limit exceeded");
  definitions.push_back(function);
  return true;
}
} // namespace ctk::clang_layer::control_flow
