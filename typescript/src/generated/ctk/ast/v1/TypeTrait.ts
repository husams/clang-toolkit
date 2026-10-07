// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

export const TypeTrait = {
  TYPE_TRAIT_UNSPECIFIED: 'TYPE_TRAIT_UNSPECIFIED',
  TYPE_TRAIT_OTHER: 'TYPE_TRAIT_OTHER',
} as const;

export type TypeTrait =
  | 'TYPE_TRAIT_UNSPECIFIED'
  | 0
  | 'TYPE_TRAIT_OTHER'
  | 1

export type TypeTrait__Output = typeof TypeTrait[keyof typeof TypeTrait]
