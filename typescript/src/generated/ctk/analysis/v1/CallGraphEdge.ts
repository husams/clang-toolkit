// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/call_graph_edge.proto

import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { FieldAvailability as _ctk_ast_v1_FieldAvailability, FieldAvailability__Output as _ctk_ast_v1_FieldAvailability__Output } from '../../../ctk/ast/v1/FieldAvailability.js';
import type { Long } from '@grpc/proto-loader';

export interface CallGraphEdge {
  'callerNode'?: (number | string | Long);
  'calleeNode'?: (number | string | Long);
  'call'?: (_ctk_ast_v1_ExpressionValue | null);
  'isVirtualRootEdge'?: (boolean);
  'isComplete'?: (boolean);
  'availability'?: (_ctk_ast_v1_FieldAvailability)[];
  '_isComplete'?: "isComplete";
}

export interface CallGraphEdge__Output {
  'callerNode': (string);
  'calleeNode': (string);
  'call': (_ctk_ast_v1_ExpressionValue__Output | null);
  'isVirtualRootEdge': (boolean);
  'isComplete'?: (boolean);
  'availability': (_ctk_ast_v1_FieldAvailability__Output)[];
  '_isComplete'?: "isComplete";
}
