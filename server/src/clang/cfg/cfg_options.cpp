#include "cfg_options.hpp"
#include "cfg_budget.hpp"
#include <clang/Basic/Version.h>
namespace ctk::clang_layer::control_flow {
clang::CFG::BuildOptions
build_options(const ctk::analysis::v1::CfgOptions &source) {
  clang::CFG::BuildOptions output;
  if (source.has_prune_trivially_false_edges())
    output.PruneTriviallyFalseEdges = source.prune_trivially_false_edges();
  output.AddEHEdges = source.add_eh_edges();
  output.AddInitializers = source.add_initializers();
  output.AddImplicitDtors = source.add_implicit_dtors();
  output.AddTemporaryDtors = source.add_temporary_dtors();
  output.AddLifetime = source.add_lifetime();
  output.AddScopes = source.add_scopes();
  output.AddLoopExit = source.add_loop_exit();
  output.AddStaticInitBranches = source.add_static_init_branches();
  output.AddCXXNewAllocator = source.add_cxx_new_allocator();
  output.AddCXXDefaultInitExprInCtors =
      source.add_cxx_default_init_expr_in_ctors();
  output.AddCXXDefaultInitExprInAggregates =
      source.add_cxx_default_init_expr_in_aggregates();
  output.AddRichCXXConstructors = source.add_rich_cxx_constructors();
  output.MarkElidedCXXConstructors = source.mark_elided_cxx_constructors();
  output.AddVirtualBaseBranches = source.add_virtual_base_branches();
  output.OmitImplicitValueInitializers =
      source.omit_implicit_value_initializers();
#if CLANG_VERSION_MAJOR >= 22
  output.AssumeReachableDefaultInSwitchStatements =
      source.assume_reachable_default_in_switch_statements();
#else
  if (source.assume_reachable_default_in_switch_statements())
    throw BuildFailure(MatchCode::FailedPrecondition,
                       "assume_reachable_default_in_switch_statements requires "
                       "Clang 22 or newer");
#endif
  if (source.always_add_statements())
    output.setAllAlwaysAdd();
  return output;
}
} // namespace ctk::clang_layer::control_flow
