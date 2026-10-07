// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/traversal_node.proto

import type { MatchBinding as _ctk_match_v1_MatchBinding, MatchBinding__Output as _ctk_match_v1_MatchBinding__Output } from '../../../ctk/match/v1/MatchBinding.js';
import type { Long } from '@grpc/proto-loader';

export interface TraversalNode {
  'parentIndex'?: (number | string | Long);
  'depth'?: (number);
  'value'?: (_ctk_match_v1_MatchBinding | null);
  '_parentIndex'?: "parentIndex";
}

export interface TraversalNode__Output {
  'parentIndex'?: (string);
  'depth': (number);
  'value': (_ctk_match_v1_MatchBinding__Output | null);
  '_parentIndex'?: "parentIndex";
}
