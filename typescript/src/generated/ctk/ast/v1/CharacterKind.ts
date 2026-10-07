// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

export const CharacterKind = {
  CHARACTER_KIND_UNSPECIFIED: 'CHARACTER_KIND_UNSPECIFIED',
  CHARACTER_KIND_ASCII: 'CHARACTER_KIND_ASCII',
  CHARACTER_KIND_UTF8: 'CHARACTER_KIND_UTF8',
  CHARACTER_KIND_UTF16: 'CHARACTER_KIND_UTF16',
  CHARACTER_KIND_UTF32: 'CHARACTER_KIND_UTF32',
  CHARACTER_KIND_WIDE: 'CHARACTER_KIND_WIDE',
} as const;

export type CharacterKind =
  | 'CHARACTER_KIND_UNSPECIFIED'
  | 0
  | 'CHARACTER_KIND_ASCII'
  | 1
  | 'CHARACTER_KIND_UTF8'
  | 2
  | 'CHARACTER_KIND_UTF16'
  | 3
  | 'CHARACTER_KIND_UTF32'
  | 4
  | 'CHARACTER_KIND_WIDE'
  | 5

export type CharacterKind__Output = typeof CharacterKind[keyof typeof CharacterKind]
