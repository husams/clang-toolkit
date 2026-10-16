// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/call_graph_stream.proto

import type { CallGraphNode as _ctk_analysis_v1_CallGraphNode, CallGraphNode__Output as _ctk_analysis_v1_CallGraphNode__Output } from '../../../ctk/analysis/v1/CallGraphNode.js';
import type { Long } from '@grpc/proto-loader';

export interface CallGraphNodeEvent {
  'graphIndex'?: (number | string | Long);
  'node'?: (_ctk_analysis_v1_CallGraphNode | null);
}

export interface CallGraphNodeEvent__Output {
  'graphIndex': (string);
  'node': (_ctk_analysis_v1_CallGraphNode__Output | null);
}
