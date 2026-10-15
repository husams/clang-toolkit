// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/traverse_stream.proto

import type { TraversalNode as _ctk_analysis_v1_TraversalNode, TraversalNode__Output as _ctk_analysis_v1_TraversalNode__Output } from '../../../ctk/analysis/v1/TraversalNode.js';
import type { TraverseCompleted as _ctk_analysis_v1_TraverseCompleted, TraverseCompleted__Output as _ctk_analysis_v1_TraverseCompleted__Output } from '../../../ctk/analysis/v1/TraverseCompleted.js';

export interface TraverseStreamEvent {
  'node'?: (_ctk_analysis_v1_TraversalNode | null);
  'completed'?: (_ctk_analysis_v1_TraverseCompleted | null);
  'event'?: "node"|"completed";
}

export interface TraverseStreamEvent__Output {
  'node'?: (_ctk_analysis_v1_TraversalNode__Output | null);
  'completed'?: (_ctk_analysis_v1_TraverseCompleted__Output | null);
  'event'?: "node"|"completed";
}
