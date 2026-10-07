// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/node.proto

export const UnsupportedReason = {
  UNSUPPORTED_REASON_UNSPECIFIED: 'UNSUPPORTED_REASON_UNSPECIFIED',
  UNSUPPORTED_REASON_EXCLUDED_LANGUAGE: 'UNSUPPORTED_REASON_EXCLUDED_LANGUAGE',
  UNSUPPORTED_REASON_DEFERRED_CONTRACT: 'UNSUPPORTED_REASON_DEFERRED_CONTRACT',
} as const;

export type UnsupportedReason =
  | 'UNSUPPORTED_REASON_UNSPECIFIED'
  | 0
  | 'UNSUPPORTED_REASON_EXCLUDED_LANGUAGE'
  | 1
  | 'UNSUPPORTED_REASON_DEFERRED_CONTRACT'
  | 2

export type UnsupportedReason__Output = typeof UnsupportedReason[keyof typeof UnsupportedReason]
