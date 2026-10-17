// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/call_graph_stream.proto

import type { MatchStreamCompleted as _ctk_match_v1_MatchStreamCompleted, MatchStreamCompleted__Output as _ctk_match_v1_MatchStreamCompleted__Output } from '../../../ctk/match/v1/MatchStreamCompleted.js';
import type { Long } from '@grpc/proto-loader';

export interface CallGraphCompleted {
  'graphCount'?: (number | string | Long);
  'nodeCount'?: (number | string | Long);
  'edgeCount'?: (number | string | Long);
  'callSiteCount'?: (number | string | Long);
  'isComplete'?: (boolean);
  'retainedNodes'?: (_ctk_match_v1_MatchStreamCompleted | null);
}

export interface CallGraphCompleted__Output {
  'graphCount': (string);
  'nodeCount': (string);
  'edgeCount': (string);
  'callSiteCount': (string);
  'isComplete': (boolean);
  'retainedNodes': (_ctk_match_v1_MatchStreamCompleted__Output | null);
}
