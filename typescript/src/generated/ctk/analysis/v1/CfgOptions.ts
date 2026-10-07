// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/cfg_options.proto


export interface CfgOptions {
  'pruneTriviallyFalseEdges'?: (boolean);
  'addEhEdges'?: (boolean);
  'addInitializers'?: (boolean);
  'addImplicitDtors'?: (boolean);
  'addTemporaryDtors'?: (boolean);
  'addLifetime'?: (boolean);
  'addScopes'?: (boolean);
  'addLoopExit'?: (boolean);
  'addStaticInitBranches'?: (boolean);
  'addCxxNewAllocator'?: (boolean);
  'addCxxDefaultInitExprInCtors'?: (boolean);
  'addCxxDefaultInitExprInAggregates'?: (boolean);
  'addRichCxxConstructors'?: (boolean);
  'markElidedCxxConstructors'?: (boolean);
  'addVirtualBaseBranches'?: (boolean);
  'omitImplicitValueInitializers'?: (boolean);
  'assumeReachableDefaultInSwitchStatements'?: (boolean);
  'alwaysAddStatements'?: (boolean);
  '_pruneTriviallyFalseEdges'?: "pruneTriviallyFalseEdges";
}

export interface CfgOptions__Output {
  'pruneTriviallyFalseEdges'?: (boolean);
  'addEhEdges': (boolean);
  'addInitializers': (boolean);
  'addImplicitDtors': (boolean);
  'addTemporaryDtors': (boolean);
  'addLifetime': (boolean);
  'addScopes': (boolean);
  'addLoopExit': (boolean);
  'addStaticInitBranches': (boolean);
  'addCxxNewAllocator': (boolean);
  'addCxxDefaultInitExprInCtors': (boolean);
  'addCxxDefaultInitExprInAggregates': (boolean);
  'addRichCxxConstructors': (boolean);
  'markElidedCxxConstructors': (boolean);
  'addVirtualBaseBranches': (boolean);
  'omitImplicitValueInitializers': (boolean);
  'assumeReachableDefaultInSwitchStatements': (boolean);
  'alwaysAddStatements': (boolean);
  '_pruneTriviallyFalseEdges'?: "pruneTriviallyFalseEdges";
}
