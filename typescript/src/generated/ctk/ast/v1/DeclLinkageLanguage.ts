// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

export const DeclLinkageLanguage = {
  DECL_LINKAGE_LANGUAGE_UNSPECIFIED: 'DECL_LINKAGE_LANGUAGE_UNSPECIFIED',
  DECL_LINKAGE_LANGUAGE_C: 'DECL_LINKAGE_LANGUAGE_C',
  DECL_LINKAGE_LANGUAGE_CXX: 'DECL_LINKAGE_LANGUAGE_CXX',
} as const;

export type DeclLinkageLanguage =
  | 'DECL_LINKAGE_LANGUAGE_UNSPECIFIED'
  | 0
  | 'DECL_LINKAGE_LANGUAGE_C'
  | 1
  | 'DECL_LINKAGE_LANGUAGE_CXX'
  | 2

export type DeclLinkageLanguage__Output = typeof DeclLinkageLanguage[keyof typeof DeclLinkageLanguage]
