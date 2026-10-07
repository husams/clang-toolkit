// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

export const SourceLocExprKind = {
  SOURCE_LOC_EXPR_KIND_UNSPECIFIED: 'SOURCE_LOC_EXPR_KIND_UNSPECIFIED',
  SOURCE_LOC_EXPR_KIND_LINE: 'SOURCE_LOC_EXPR_KIND_LINE',
  SOURCE_LOC_EXPR_KIND_COLUMN: 'SOURCE_LOC_EXPR_KIND_COLUMN',
  SOURCE_LOC_EXPR_KIND_FILE: 'SOURCE_LOC_EXPR_KIND_FILE',
  SOURCE_LOC_EXPR_KIND_FUNCTION: 'SOURCE_LOC_EXPR_KIND_FUNCTION',
} as const;

export type SourceLocExprKind =
  | 'SOURCE_LOC_EXPR_KIND_UNSPECIFIED'
  | 0
  | 'SOURCE_LOC_EXPR_KIND_LINE'
  | 1
  | 'SOURCE_LOC_EXPR_KIND_COLUMN'
  | 2
  | 'SOURCE_LOC_EXPR_KIND_FILE'
  | 3
  | 'SOURCE_LOC_EXPR_KIND_FUNCTION'
  | 4

export type SourceLocExprKind__Output = typeof SourceLocExprKind[keyof typeof SourceLocExprKind]
