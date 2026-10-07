// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/common.proto

export const AccessSpecifier = {
  ACCESS_SPECIFIER_UNSPECIFIED: 'ACCESS_SPECIFIER_UNSPECIFIED',
  ACCESS_SPECIFIER_NONE: 'ACCESS_SPECIFIER_NONE',
  ACCESS_SPECIFIER_PUBLIC: 'ACCESS_SPECIFIER_PUBLIC',
  ACCESS_SPECIFIER_PROTECTED: 'ACCESS_SPECIFIER_PROTECTED',
  ACCESS_SPECIFIER_PRIVATE: 'ACCESS_SPECIFIER_PRIVATE',
} as const;

export type AccessSpecifier =
  | 'ACCESS_SPECIFIER_UNSPECIFIED'
  | 0
  | 'ACCESS_SPECIFIER_NONE'
  | 1
  | 'ACCESS_SPECIFIER_PUBLIC'
  | 2
  | 'ACCESS_SPECIFIER_PROTECTED'
  | 3
  | 'ACCESS_SPECIFIER_PRIVATE'
  | 4

export type AccessSpecifier__Output = typeof AccessSpecifier[keyof typeof AccessSpecifier]
