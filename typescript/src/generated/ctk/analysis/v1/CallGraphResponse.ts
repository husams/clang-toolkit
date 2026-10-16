// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/call_graph_response.proto

import type { CallGraphNode as _ctk_analysis_v1_CallGraphNode, CallGraphNode__Output as _ctk_analysis_v1_CallGraphNode__Output } from '../../../ctk/analysis/v1/CallGraphNode.js';
import type { CallGraphEdge as _ctk_analysis_v1_CallGraphEdge, CallGraphEdge__Output as _ctk_analysis_v1_CallGraphEdge__Output } from '../../../ctk/analysis/v1/CallGraphEdge.js';
import type { FieldAvailability as _ctk_ast_v1_FieldAvailability, FieldAvailability__Output as _ctk_ast_v1_FieldAvailability__Output } from '../../../ctk/ast/v1/FieldAvailability.js';
import type { CallGraphCallSite as _ctk_analysis_v1_CallGraphCallSite, CallGraphCallSite__Output as _ctk_analysis_v1_CallGraphCallSite__Output } from '../../../ctk/analysis/v1/CallGraphCallSite.js';
import type { CallGraphDirection as _ctk_analysis_v1_CallGraphDirection, CallGraphDirection__Output as _ctk_analysis_v1_CallGraphDirection__Output } from '../../../ctk/analysis/v1/CallGraphDirection.js';
import type { Long } from '@grpc/proto-loader';

export interface CallGraphResponse {
  'rootNode'?: (number | string | Long);
  'nodes'?: (_ctk_analysis_v1_CallGraphNode)[];
  'edges'?: (_ctk_analysis_v1_CallGraphEdge)[];
  'isComplete'?: (boolean);
  'availability'?: (_ctk_ast_v1_FieldAvailability)[];
  'mainFileOnly'?: (boolean);
  'externalEdgesOmitted'?: (number | string | Long);
  'callSites'?: (_ctk_analysis_v1_CallGraphCallSite)[];
  'snapshotGeneration'?: (number | string | Long);
  'sourceFile'?: (string);
  'sourceRevision'?: (string);
  'compilationProfileId'?: (string);
  'focusNode'?: (number | string | Long);
  'selectionDirection'?: (_ctk_analysis_v1_CallGraphDirection);
  'selectionMaxDepth'?: (number | string | Long);
  'selectionBoundaryEdges'?: (number | string | Long);
  'selectionBoundaryCallSites'?: (number | string | Long);
  'selectionUnlimitedDepth'?: (boolean);
  '_isComplete'?: "isComplete";
  '_focusNode'?: "focusNode";
  '_selectionMaxDepth'?: "selectionMaxDepth";
  '_selectionUnlimitedDepth'?: "selectionUnlimitedDepth";
}

export interface CallGraphResponse__Output {
  'rootNode': (string);
  'nodes': (_ctk_analysis_v1_CallGraphNode__Output)[];
  'edges': (_ctk_analysis_v1_CallGraphEdge__Output)[];
  'isComplete'?: (boolean);
  'availability': (_ctk_ast_v1_FieldAvailability__Output)[];
  'mainFileOnly': (boolean);
  'externalEdgesOmitted': (string);
  'callSites': (_ctk_analysis_v1_CallGraphCallSite__Output)[];
  'snapshotGeneration': (string);
  'sourceFile': (string);
  'sourceRevision': (string);
  'compilationProfileId': (string);
  'focusNode'?: (string);
  'selectionDirection': (_ctk_analysis_v1_CallGraphDirection__Output);
  'selectionMaxDepth'?: (string);
  'selectionBoundaryEdges': (string);
  'selectionBoundaryCallSites': (string);
  'selectionUnlimitedDepth'?: (boolean);
  '_isComplete'?: "isComplete";
  '_focusNode'?: "focusNode";
  '_selectionMaxDepth'?: "selectionMaxDepth";
  '_selectionUnlimitedDepth'?: "selectionUnlimitedDepth";
}
