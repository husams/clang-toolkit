// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

export const AutoKeyword = {
  AUTO_KEYWORD_UNSPECIFIED: 'AUTO_KEYWORD_UNSPECIFIED',
  AUTO_KEYWORD_AUTO: 'AUTO_KEYWORD_AUTO',
  AUTO_KEYWORD_DECLTYPE_AUTO: 'AUTO_KEYWORD_DECLTYPE_AUTO',
  AUTO_KEYWORD_GNU_AUTO_TYPE: 'AUTO_KEYWORD_GNU_AUTO_TYPE',
} as const;

export type AutoKeyword =
  | 'AUTO_KEYWORD_UNSPECIFIED'
  | 0
  | 'AUTO_KEYWORD_AUTO'
  | 1
  | 'AUTO_KEYWORD_DECLTYPE_AUTO'
  | 2
  | 'AUTO_KEYWORD_GNU_AUTO_TYPE'
  | 3

export type AutoKeyword__Output = typeof AutoKeyword[keyof typeof AutoKeyword]
