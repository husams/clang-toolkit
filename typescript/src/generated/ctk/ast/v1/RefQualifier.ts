// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/common.proto

export const RefQualifier = {
  REF_QUALIFIER_UNSPECIFIED: 'REF_QUALIFIER_UNSPECIFIED',
  REF_QUALIFIER_NONE: 'REF_QUALIFIER_NONE',
  REF_QUALIFIER_LVALUE: 'REF_QUALIFIER_LVALUE',
  REF_QUALIFIER_RVALUE: 'REF_QUALIFIER_RVALUE',
} as const;

export type RefQualifier =
  | 'REF_QUALIFIER_UNSPECIFIED'
  | 0
  | 'REF_QUALIFIER_NONE'
  | 1
  | 'REF_QUALIFIER_LVALUE'
  | 2
  | 'REF_QUALIFIER_RVALUE'
  | 3

export type RefQualifier__Output = typeof RefQualifier[keyof typeof RefQualifier]
