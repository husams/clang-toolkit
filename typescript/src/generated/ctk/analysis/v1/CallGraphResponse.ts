// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/call_graph_response.proto

import type { CallGraphNode as _ctk_analysis_v1_CallGraphNode, CallGraphNode__Output as _ctk_analysis_v1_CallGraphNode__Output } from '../../../ctk/analysis/v1/CallGraphNode.js';
import type { CallGraphEdge as _ctk_analysis_v1_CallGraphEdge, CallGraphEdge__Output as _ctk_analysis_v1_CallGraphEdge__Output } from '../../../ctk/analysis/v1/CallGraphEdge.js';
import type { FieldAvailability as _ctk_ast_v1_FieldAvailability, FieldAvailability__Output as _ctk_ast_v1_FieldAvailability__Output } from '../../../ctk/ast/v1/FieldAvailability.js';
import type { Long } from '@grpc/proto-loader';

export interface CallGraphResponse {
  'rootNode'?: (number | string | Long);
  'nodes'?: (_ctk_analysis_v1_CallGraphNode)[];
  'edges'?: (_ctk_analysis_v1_CallGraphEdge)[];
  'isComplete'?: (boolean);
  'availability'?: (_ctk_ast_v1_FieldAvailability)[];
  '_isComplete'?: "isComplete";
}

export interface CallGraphResponse__Output {
  'rootNode': (string);
  'nodes': (_ctk_analysis_v1_CallGraphNode__Output)[];
  'edges': (_ctk_analysis_v1_CallGraphEdge__Output)[];
  'isComplete'?: (boolean);
  'availability': (_ctk_ast_v1_FieldAvailability__Output)[];
  '_isComplete'?: "isComplete";
}
