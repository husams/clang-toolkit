// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

export const ArraySizeModifier = {
  ARRAY_SIZE_MODIFIER_UNSPECIFIED: 'ARRAY_SIZE_MODIFIER_UNSPECIFIED',
  ARRAY_SIZE_MODIFIER_NORMAL: 'ARRAY_SIZE_MODIFIER_NORMAL',
  ARRAY_SIZE_MODIFIER_STATIC: 'ARRAY_SIZE_MODIFIER_STATIC',
  ARRAY_SIZE_MODIFIER_STAR: 'ARRAY_SIZE_MODIFIER_STAR',
} as const;

export type ArraySizeModifier =
  | 'ARRAY_SIZE_MODIFIER_UNSPECIFIED'
  | 0
  | 'ARRAY_SIZE_MODIFIER_NORMAL'
  | 1
  | 'ARRAY_SIZE_MODIFIER_STATIC'
  | 2
  | 'ARRAY_SIZE_MODIFIER_STAR'
  | 3

export type ArraySizeModifier__Output = typeof ArraySizeModifier[keyof typeof ArraySizeModifier]
