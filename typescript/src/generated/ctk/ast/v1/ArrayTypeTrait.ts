// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

export const ArrayTypeTrait = {
  ARRAY_TYPE_TRAIT_UNSPECIFIED: 'ARRAY_TYPE_TRAIT_UNSPECIFIED',
  ARRAY_TYPE_TRAIT_COUNT: 'ARRAY_TYPE_TRAIT_COUNT',
} as const;

export type ArrayTypeTrait =
  | 'ARRAY_TYPE_TRAIT_UNSPECIFIED'
  | 0
  | 'ARRAY_TYPE_TRAIT_COUNT'
  | 1

export type ArrayTypeTrait__Output = typeof ArrayTypeTrait[keyof typeof ArrayTypeTrait]
