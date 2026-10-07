// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/common.proto

export const TagKind = {
  TAG_KIND_UNSPECIFIED: 'TAG_KIND_UNSPECIFIED',
  TAG_KIND_STRUCT: 'TAG_KIND_STRUCT',
  TAG_KIND_UNION: 'TAG_KIND_UNION',
  TAG_KIND_CLASS: 'TAG_KIND_CLASS',
  TAG_KIND_ENUM: 'TAG_KIND_ENUM',
  TAG_KIND_INTERFACE: 'TAG_KIND_INTERFACE',
} as const;

export type TagKind =
  | 'TAG_KIND_UNSPECIFIED'
  | 0
  | 'TAG_KIND_STRUCT'
  | 1
  | 'TAG_KIND_UNION'
  | 2
  | 'TAG_KIND_CLASS'
  | 3
  | 'TAG_KIND_ENUM'
  | 4
  | 'TAG_KIND_INTERFACE'
  | 5

export type TagKind__Output = typeof TagKind[keyof typeof TagKind]
