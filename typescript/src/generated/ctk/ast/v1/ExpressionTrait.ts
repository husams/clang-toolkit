// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

export const ExpressionTrait = {
  EXPRESSION_TRAIT_UNSPECIFIED: 'EXPRESSION_TRAIT_UNSPECIFIED',
  EXPRESSION_TRAIT_IS_LVALUE: 'EXPRESSION_TRAIT_IS_LVALUE',
  EXPRESSION_TRAIT_IS_XVALUE: 'EXPRESSION_TRAIT_IS_XVALUE',
  EXPRESSION_TRAIT_IS_PRVALUE: 'EXPRESSION_TRAIT_IS_PRVALUE',
  EXPRESSION_TRAIT_OTHER: 'EXPRESSION_TRAIT_OTHER',
} as const;

export type ExpressionTrait =
  | 'EXPRESSION_TRAIT_UNSPECIFIED'
  | 0
  | 'EXPRESSION_TRAIT_IS_LVALUE'
  | 1
  | 'EXPRESSION_TRAIT_IS_XVALUE'
  | 2
  | 'EXPRESSION_TRAIT_IS_PRVALUE'
  | 3
  | 'EXPRESSION_TRAIT_OTHER'
  | 4

export type ExpressionTrait__Output = typeof ExpressionTrait[keyof typeof ExpressionTrait]
