// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_result.proto

import type { MatchSourcePoint as _ctk_match_v1_MatchSourcePoint, MatchSourcePoint__Output as _ctk_match_v1_MatchSourcePoint__Output } from '../../../ctk/match/v1/MatchSourcePoint.js';

export interface MatchSourceRange {
  'expansionBegin'?: (_ctk_match_v1_MatchSourcePoint | null);
  'expansionEnd'?: (_ctk_match_v1_MatchSourcePoint | null);
  'spellingBegin'?: (_ctk_match_v1_MatchSourcePoint | null);
  'spellingEnd'?: (_ctk_match_v1_MatchSourcePoint | null);
  'expansionEndExclusive'?: (_ctk_match_v1_MatchSourcePoint | null);
  'spellingEndExclusive'?: (_ctk_match_v1_MatchSourcePoint | null);
}

export interface MatchSourceRange__Output {
  'expansionBegin': (_ctk_match_v1_MatchSourcePoint__Output | null);
  'expansionEnd': (_ctk_match_v1_MatchSourcePoint__Output | null);
  'spellingBegin': (_ctk_match_v1_MatchSourcePoint__Output | null);
  'spellingEnd': (_ctk_match_v1_MatchSourcePoint__Output | null);
  'expansionEndExclusive': (_ctk_match_v1_MatchSourcePoint__Output | null);
  'spellingEndExclusive': (_ctk_match_v1_MatchSourcePoint__Output | null);
}
