// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/parse_response.proto

import type { Timestamp as _google_protobuf_Timestamp, Timestamp__Output as _google_protobuf_Timestamp__Output } from '../../../google/protobuf/Timestamp.js';
import type { Long } from '@grpc/proto-loader';

export interface ParseResponse {
  'sessionId'?: (string);
  'resultRevision'?: (number | string | Long);
  'expiresAt'?: (_google_protobuf_Timestamp | null);
}

export interface ParseResponse__Output {
  'sessionId': (string);
  'resultRevision': (string);
  'expiresAt': (_google_protobuf_Timestamp__Output | null);
}
