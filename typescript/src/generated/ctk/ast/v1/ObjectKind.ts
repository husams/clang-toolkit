// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/common.proto

export const ObjectKind = {
  OBJECT_KIND_UNSPECIFIED: 'OBJECT_KIND_UNSPECIFIED',
  OBJECT_KIND_ORDINARY: 'OBJECT_KIND_ORDINARY',
  OBJECT_KIND_BIT_FIELD: 'OBJECT_KIND_BIT_FIELD',
  OBJECT_KIND_VECTOR_COMPONENT: 'OBJECT_KIND_VECTOR_COMPONENT',
  OBJECT_KIND_MATRIX_COMPONENT: 'OBJECT_KIND_MATRIX_COMPONENT',
} as const;

export type ObjectKind =
  | 'OBJECT_KIND_UNSPECIFIED'
  | 0
  | 'OBJECT_KIND_ORDINARY'
  | 1
  | 'OBJECT_KIND_BIT_FIELD'
  | 2
  | 'OBJECT_KIND_VECTOR_COMPONENT'
  | 3
  | 'OBJECT_KIND_MATRIX_COMPONENT'
  | 4

export type ObjectKind__Output = typeof ObjectKind[keyof typeof ObjectKind]
