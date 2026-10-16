// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/call_graph_stream.proto

import type { CallGraphEdge as _ctk_analysis_v1_CallGraphEdge, CallGraphEdge__Output as _ctk_analysis_v1_CallGraphEdge__Output } from '../../../ctk/analysis/v1/CallGraphEdge.js';
import type { Long } from '@grpc/proto-loader';

export interface CallGraphEdgeEvent {
  'graphIndex'?: (number | string | Long);
  'edge'?: (_ctk_analysis_v1_CallGraphEdge | null);
}

export interface CallGraphEdgeEvent__Output {
  'graphIndex': (string);
  'edge': (_ctk_analysis_v1_CallGraphEdge__Output | null);
}
