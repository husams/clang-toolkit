// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

export const DeclVariableTLSKind = {
  DECL_VARIABLE_TLS_KIND_UNSPECIFIED: 'DECL_VARIABLE_TLS_KIND_UNSPECIFIED',
  DECL_VARIABLE_TLS_KIND_NONE: 'DECL_VARIABLE_TLS_KIND_NONE',
  DECL_VARIABLE_TLS_KIND_STATIC: 'DECL_VARIABLE_TLS_KIND_STATIC',
  DECL_VARIABLE_TLS_KIND_DYNAMIC: 'DECL_VARIABLE_TLS_KIND_DYNAMIC',
} as const;

export type DeclVariableTLSKind =
  | 'DECL_VARIABLE_TLS_KIND_UNSPECIFIED'
  | 0
  | 'DECL_VARIABLE_TLS_KIND_NONE'
  | 1
  | 'DECL_VARIABLE_TLS_KIND_STATIC'
  | 2
  | 'DECL_VARIABLE_TLS_KIND_DYNAMIC'
  | 3

export type DeclVariableTLSKind__Output = typeof DeclVariableTLSKind[keyof typeof DeclVariableTLSKind]
