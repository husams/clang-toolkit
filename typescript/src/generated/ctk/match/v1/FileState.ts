// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/resources.proto

export const FileState = {
  FILE_STATE_UNSPECIFIED: 'FILE_STATE_UNSPECIFIED',
  FILE_STATE_OPENING: 'FILE_STATE_OPENING',
  FILE_STATE_OPEN: 'FILE_STATE_OPEN',
  FILE_STATE_PINNED: 'FILE_STATE_PINNED',
  FILE_STATE_CLOSING: 'FILE_STATE_CLOSING',
  FILE_STATE_FAILED: 'FILE_STATE_FAILED',
  FILE_STATE_CLOSED: 'FILE_STATE_CLOSED',
} as const;

export type FileState =
  | 'FILE_STATE_UNSPECIFIED'
  | 0
  | 'FILE_STATE_OPENING'
  | 1
  | 'FILE_STATE_OPEN'
  | 2
  | 'FILE_STATE_PINNED'
  | 3
  | 'FILE_STATE_CLOSING'
  | 4
  | 'FILE_STATE_FAILED'
  | 5
  | 'FILE_STATE_CLOSED'
  | 6

export type FileState__Output = typeof FileState[keyof typeof FileState]
