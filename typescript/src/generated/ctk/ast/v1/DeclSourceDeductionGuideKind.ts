// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

export const DeclSourceDeductionGuideKind = {
  DECL_SOURCE_DEDUCTION_GUIDE_KIND_UNSPECIFIED: 'DECL_SOURCE_DEDUCTION_GUIDE_KIND_UNSPECIFIED',
  DECL_SOURCE_DEDUCTION_GUIDE_KIND_NONE: 'DECL_SOURCE_DEDUCTION_GUIDE_KIND_NONE',
  DECL_SOURCE_DEDUCTION_GUIDE_KIND_ALIAS: 'DECL_SOURCE_DEDUCTION_GUIDE_KIND_ALIAS',
} as const;

export type DeclSourceDeductionGuideKind =
  | 'DECL_SOURCE_DEDUCTION_GUIDE_KIND_UNSPECIFIED'
  | 0
  | 'DECL_SOURCE_DEDUCTION_GUIDE_KIND_NONE'
  | 1
  | 'DECL_SOURCE_DEDUCTION_GUIDE_KIND_ALIAS'
  | 2

export type DeclSourceDeductionGuideKind__Output = typeof DeclSourceDeductionGuideKind[keyof typeof DeclSourceDeductionGuideKind]
