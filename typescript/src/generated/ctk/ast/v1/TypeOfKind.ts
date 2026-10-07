// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

export const TypeOfKind = {
  TYPE_OF_KIND_UNSPECIFIED: 'TYPE_OF_KIND_UNSPECIFIED',
  TYPE_OF_KIND_QUALIFIED: 'TYPE_OF_KIND_QUALIFIED',
  TYPE_OF_KIND_UNQUALIFIED: 'TYPE_OF_KIND_UNQUALIFIED',
} as const;

export type TypeOfKind =
  | 'TYPE_OF_KIND_UNSPECIFIED'
  | 0
  | 'TYPE_OF_KIND_QUALIFIED'
  | 1
  | 'TYPE_OF_KIND_UNQUALIFIED'
  | 2

export type TypeOfKind__Output = typeof TypeOfKind[keyof typeof TypeOfKind]
