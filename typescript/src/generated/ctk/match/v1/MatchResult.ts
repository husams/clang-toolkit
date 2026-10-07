// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_result.proto

import type { MatchBinding as _ctk_match_v1_MatchBinding, MatchBinding__Output as _ctk_match_v1_MatchBinding__Output } from '../../../ctk/match/v1/MatchBinding.js';
import type { Long } from '@grpc/proto-loader';

export interface MatchResult {
  'bindings'?: ({[key: string]: _ctk_match_v1_MatchBinding});
  'sourceMatchIndex'?: (number | string | Long);
  '_sourceMatchIndex'?: "sourceMatchIndex";
}

export interface MatchResult__Output {
  'bindings': ({[key: string]: _ctk_match_v1_MatchBinding__Output});
  'sourceMatchIndex'?: (string);
  '_sourceMatchIndex'?: "sourceMatchIndex";
}
