// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

export const PredefinedTypeKind = {
  PREDEFINED_TYPE_KIND_UNSPECIFIED: 'PREDEFINED_TYPE_KIND_UNSPECIFIED',
  PREDEFINED_TYPE_KIND_SIZE_T: 'PREDEFINED_TYPE_KIND_SIZE_T',
  PREDEFINED_TYPE_KIND_SIGNED_SIZE_T: 'PREDEFINED_TYPE_KIND_SIGNED_SIZE_T',
  PREDEFINED_TYPE_KIND_PTRDIFF_T: 'PREDEFINED_TYPE_KIND_PTRDIFF_T',
} as const;

export type PredefinedTypeKind =
  | 'PREDEFINED_TYPE_KIND_UNSPECIFIED'
  | 0
  | 'PREDEFINED_TYPE_KIND_SIZE_T'
  | 1
  | 'PREDEFINED_TYPE_KIND_SIGNED_SIZE_T'
  | 2
  | 'PREDEFINED_TYPE_KIND_PTRDIFF_T'
  | 3

export type PredefinedTypeKind__Output = typeof PredefinedTypeKind[keyof typeof PredefinedTypeKind]
