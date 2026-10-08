// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_stream.proto

import type { MatchResult as _ctk_match_v1_MatchResult, MatchResult__Output as _ctk_match_v1_MatchResult__Output } from '../../../ctk/match/v1/MatchResult.js';
import type { MatchStreamCompleted as _ctk_match_v1_MatchStreamCompleted, MatchStreamCompleted__Output as _ctk_match_v1_MatchStreamCompleted__Output } from '../../../ctk/match/v1/MatchStreamCompleted.js';

export interface MatchStreamEvent {
  'row'?: (_ctk_match_v1_MatchResult | null);
  'completed'?: (_ctk_match_v1_MatchStreamCompleted | null);
  'event'?: "row"|"completed";
}

export interface MatchStreamEvent__Output {
  'row'?: (_ctk_match_v1_MatchResult__Output | null);
  'completed'?: (_ctk_match_v1_MatchStreamCompleted__Output | null);
  'event'?: "row"|"completed";
}
