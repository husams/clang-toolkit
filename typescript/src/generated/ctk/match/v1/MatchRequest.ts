// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_service.proto

import type { FileMatchTarget as _ctk_match_v1_FileMatchTarget, FileMatchTarget__Output as _ctk_match_v1_FileMatchTarget__Output } from '../../../ctk/match/v1/FileMatchTarget.js';
import type { SessionMatchTarget as _ctk_match_v1_SessionMatchTarget, SessionMatchTarget__Output as _ctk_match_v1_SessionMatchTarget__Output } from '../../../ctk/match/v1/SessionMatchTarget.js';
import type { BindingMatchTarget as _ctk_match_v1_BindingMatchTarget, BindingMatchTarget__Output as _ctk_match_v1_BindingMatchTarget__Output } from '../../../ctk/match/v1/BindingMatchTarget.js';
import type { MatchTraversalMode as _ctk_match_v1_MatchTraversalMode, MatchTraversalMode__Output as _ctk_match_v1_MatchTraversalMode__Output } from '../../../ctk/match/v1/MatchTraversalMode.js';

export interface MatchRequest {
  'query'?: (string);
  'file'?: (_ctk_match_v1_FileMatchTarget | null);
  'session'?: (_ctk_match_v1_SessionMatchTarget | null);
  'binding'?: (_ctk_match_v1_BindingMatchTarget | null);
  'traversalMode'?: (_ctk_match_v1_MatchTraversalMode);
  'preserveSource'?: (boolean);
  'target'?: "file"|"session"|"binding";
}

export interface MatchRequest__Output {
  'query': (string);
  'file'?: (_ctk_match_v1_FileMatchTarget__Output | null);
  'session'?: (_ctk_match_v1_SessionMatchTarget__Output | null);
  'binding'?: (_ctk_match_v1_BindingMatchTarget__Output | null);
  'traversalMode': (_ctk_match_v1_MatchTraversalMode__Output);
  'preserveSource': (boolean);
  'target'?: "file"|"session"|"binding";
}
