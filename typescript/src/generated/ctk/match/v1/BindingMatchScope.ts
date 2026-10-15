// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_result.proto

export const BindingMatchScope = {
  BINDING_MATCH_SCOPE_UNSPECIFIED: 'BINDING_MATCH_SCOPE_UNSPECIFIED',
  BINDING_MATCH_SCOPE_ROOT_ONLY: 'BINDING_MATCH_SCOPE_ROOT_ONLY',
  BINDING_MATCH_SCOPE_SUBTREE: 'BINDING_MATCH_SCOPE_SUBTREE',
  BINDING_MATCH_SCOPE_CHILDREN: 'BINDING_MATCH_SCOPE_CHILDREN',
} as const;

export type BindingMatchScope =
  | 'BINDING_MATCH_SCOPE_UNSPECIFIED'
  | 0
  | 'BINDING_MATCH_SCOPE_ROOT_ONLY'
  | 1
  | 'BINDING_MATCH_SCOPE_SUBTREE'
  | 2
  | 'BINDING_MATCH_SCOPE_CHILDREN'
  | 3

export type BindingMatchScope__Output = typeof BindingMatchScope[keyof typeof BindingMatchScope]
