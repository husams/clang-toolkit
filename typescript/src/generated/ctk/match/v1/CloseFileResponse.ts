// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/resources.proto

import type { FileInfo as _ctk_match_v1_FileInfo, FileInfo__Output as _ctk_match_v1_FileInfo__Output } from '../../../ctk/match/v1/FileInfo.js';
import type { Long } from '@grpc/proto-loader';

export interface CloseFileResponse {
  'releasedLeases'?: (number | string | Long);
  'closedCursors'?: (number | string | Long);
  'remaining'?: (_ctk_match_v1_FileInfo)[];
}

export interface CloseFileResponse__Output {
  'releasedLeases': (string);
  'closedCursors': (string);
  'remaining': (_ctk_match_v1_FileInfo__Output)[];
}
