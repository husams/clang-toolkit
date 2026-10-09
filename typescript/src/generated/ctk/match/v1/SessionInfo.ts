// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_service.proto

import type { Timestamp as _google_protobuf_Timestamp, Timestamp__Output as _google_protobuf_Timestamp__Output } from '../../../google/protobuf/Timestamp.js';
import type { Long } from '@grpc/proto-loader';

export interface SessionInfo {
  'sessionId'?: (string);
  'resultRevision'?: (number | string | Long);
  'filePath'?: (string);
  'rowCount'?: (number | string | Long);
  'bindingNames'?: (string)[];
  'expiresAt'?: (_google_protobuf_Timestamp | null);
}

export interface SessionInfo__Output {
  'sessionId': (string);
  'resultRevision': (string);
  'filePath': (string);
  'rowCount': (string);
  'bindingNames': (string)[];
  'expiresAt': (_google_protobuf_Timestamp__Output | null);
}
