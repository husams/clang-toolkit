// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_result.proto

export const CallDispatch = {
  CALL_DISPATCH_UNSPECIFIED: 'CALL_DISPATCH_UNSPECIFIED',
  CALL_DISPATCH_DIRECT: 'CALL_DISPATCH_DIRECT',
  CALL_DISPATCH_INDIRECT: 'CALL_DISPATCH_INDIRECT',
  CALL_DISPATCH_VIRTUAL: 'CALL_DISPATCH_VIRTUAL',
} as const;

export type CallDispatch =
  | 'CALL_DISPATCH_UNSPECIFIED'
  | 0
  | 'CALL_DISPATCH_DIRECT'
  | 1
  | 'CALL_DISPATCH_INDIRECT'
  | 2
  | 'CALL_DISPATCH_VIRTUAL'
  | 3

export type CallDispatch__Output = typeof CallDispatch[keyof typeof CallDispatch]
