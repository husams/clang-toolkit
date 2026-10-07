// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_service.proto

import type { Long } from '@grpc/proto-loader';

export interface SessionMatchTarget {
  'sessionId'?: (string);
  'expectedResultRevision'?: (number | string | Long);
  '_expectedResultRevision'?: "expectedResultRevision";
}

export interface SessionMatchTarget__Output {
  'sessionId': (string);
  'expectedResultRevision'?: (string);
  '_expectedResultRevision'?: "expectedResultRevision";
}
