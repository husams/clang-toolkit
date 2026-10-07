// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/common.proto

export const ValueCategory = {
  VALUE_CATEGORY_UNSPECIFIED: 'VALUE_CATEGORY_UNSPECIFIED',
  VALUE_CATEGORY_PRVALUE: 'VALUE_CATEGORY_PRVALUE',
  VALUE_CATEGORY_LVALUE: 'VALUE_CATEGORY_LVALUE',
  VALUE_CATEGORY_XVALUE: 'VALUE_CATEGORY_XVALUE',
} as const;

export type ValueCategory =
  | 'VALUE_CATEGORY_UNSPECIFIED'
  | 0
  | 'VALUE_CATEGORY_PRVALUE'
  | 1
  | 'VALUE_CATEGORY_LVALUE'
  | 2
  | 'VALUE_CATEGORY_XVALUE'
  | 3

export type ValueCategory__Output = typeof ValueCategory[keyof typeof ValueCategory]
