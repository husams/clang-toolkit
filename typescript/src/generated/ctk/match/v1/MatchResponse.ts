// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_service.proto

import type { MatchResult as _ctk_match_v1_MatchResult, MatchResult__Output as _ctk_match_v1_MatchResult__Output } from '../../../ctk/match/v1/MatchResult.js';
import type { Timestamp as _google_protobuf_Timestamp, Timestamp__Output as _google_protobuf_Timestamp__Output } from '../../../google/protobuf/Timestamp.js';
import type { Long } from '@grpc/proto-loader';

export interface MatchResponse {
  'sessionId'?: (string);
  'resultRevision'?: (number | string | Long);
  'results'?: (_ctk_match_v1_MatchResult)[];
  'expiresAt'?: (_google_protobuf_Timestamp | null);
}

export interface MatchResponse__Output {
  'sessionId': (string);
  'resultRevision': (string);
  'results': (_ctk_match_v1_MatchResult__Output)[];
  'expiresAt': (_google_protobuf_Timestamp__Output | null);
}
