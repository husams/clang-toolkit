// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_service.proto

import type { BindingMatchScope as _ctk_match_v1_BindingMatchScope, BindingMatchScope__Output as _ctk_match_v1_BindingMatchScope__Output } from '../../../ctk/match/v1/BindingMatchScope.js';
import type { Long } from '@grpc/proto-loader';

export interface BindingMatchTarget {
  'sessionId'?: (string);
  'bind'?: (string);
  'matchIndex'?: (number | string | Long);
  'scope'?: (_ctk_match_v1_BindingMatchScope);
  'expectedResultRevision'?: (number | string | Long);
  '_matchIndex'?: "matchIndex";
  '_expectedResultRevision'?: "expectedResultRevision";
}

export interface BindingMatchTarget__Output {
  'sessionId': (string);
  'bind': (string);
  'matchIndex'?: (string);
  'scope': (_ctk_match_v1_BindingMatchScope__Output);
  'expectedResultRevision'?: (string);
  '_matchIndex'?: "matchIndex";
  '_expectedResultRevision'?: "expectedResultRevision";
}
