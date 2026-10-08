// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_stream.proto

import type { Timestamp as _google_protobuf_Timestamp, Timestamp__Output as _google_protobuf_Timestamp__Output } from '../../../google/protobuf/Timestamp.js';
import type { Long } from '@grpc/proto-loader';

export interface MatchStreamCompleted {
  'sessionId'?: (string);
  'resultRevision'?: (number | string | Long);
  'expiresAt'?: (_google_protobuf_Timestamp | null);
  'rowCount'?: (number | string | Long);
}

export interface MatchStreamCompleted__Output {
  'sessionId': (string);
  'resultRevision': (string);
  'expiresAt': (_google_protobuf_Timestamp__Output | null);
  'rowCount': (string);
}
