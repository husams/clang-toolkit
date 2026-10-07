// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/traverse_response.proto

import type { TraversalNode as _ctk_analysis_v1_TraversalNode, TraversalNode__Output as _ctk_analysis_v1_TraversalNode__Output } from '../../../ctk/analysis/v1/TraversalNode.js';

export interface TraverseResponse {
  'nodes'?: (_ctk_analysis_v1_TraversalNode)[];
  'depthLimited'?: (boolean);
}

export interface TraverseResponse__Output {
  'nodes': (_ctk_analysis_v1_TraversalNode__Output)[];
  'depthLimited': (boolean);
}
