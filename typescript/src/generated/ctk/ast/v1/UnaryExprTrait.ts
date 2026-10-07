// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

export const UnaryExprTrait = {
  UNARY_EXPR_TRAIT_UNSPECIFIED: 'UNARY_EXPR_TRAIT_UNSPECIFIED',
  UNARY_EXPR_TRAIT_SIZEOF: 'UNARY_EXPR_TRAIT_SIZEOF',
  UNARY_EXPR_TRAIT_ALIGNOF: 'UNARY_EXPR_TRAIT_ALIGNOF',
  UNARY_EXPR_TRAIT_OTHER: 'UNARY_EXPR_TRAIT_OTHER',
} as const;

export type UnaryExprTrait =
  | 'UNARY_EXPR_TRAIT_UNSPECIFIED'
  | 0
  | 'UNARY_EXPR_TRAIT_SIZEOF'
  | 1
  | 'UNARY_EXPR_TRAIT_ALIGNOF'
  | 2
  | 'UNARY_EXPR_TRAIT_OTHER'
  | 3

export type UnaryExprTrait__Output = typeof UnaryExprTrait[keyof typeof UnaryExprTrait]
