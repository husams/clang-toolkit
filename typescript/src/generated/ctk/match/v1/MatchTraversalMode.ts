// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_service.proto

export const MatchTraversalMode = {
  MATCH_TRAVERSAL_MODE_UNSPECIFIED: 'MATCH_TRAVERSAL_MODE_UNSPECIFIED',
  MATCH_TRAVERSAL_MODE_AS_IS: 'MATCH_TRAVERSAL_MODE_AS_IS',
  MATCH_TRAVERSAL_MODE_IGNORE_UNLESS_SPELLED_IN_SOURCE: 'MATCH_TRAVERSAL_MODE_IGNORE_UNLESS_SPELLED_IN_SOURCE',
} as const;

export type MatchTraversalMode =
  | 'MATCH_TRAVERSAL_MODE_UNSPECIFIED'
  | 0
  | 'MATCH_TRAVERSAL_MODE_AS_IS'
  | 1
  | 'MATCH_TRAVERSAL_MODE_IGNORE_UNLESS_SPELLED_IN_SOURCE'
  | 2

export type MatchTraversalMode__Output = typeof MatchTraversalMode[keyof typeof MatchTraversalMode]
