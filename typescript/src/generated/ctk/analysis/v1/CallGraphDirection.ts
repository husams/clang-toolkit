// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/call_graph_request.proto

export const CallGraphDirection = {
  CALL_GRAPH_DIRECTION_UNSPECIFIED: 'CALL_GRAPH_DIRECTION_UNSPECIFIED',
  CALL_GRAPH_DIRECTION_OUT: 'CALL_GRAPH_DIRECTION_OUT',
  CALL_GRAPH_DIRECTION_IN: 'CALL_GRAPH_DIRECTION_IN',
  CALL_GRAPH_DIRECTION_BOTH: 'CALL_GRAPH_DIRECTION_BOTH',
} as const;

export type CallGraphDirection =
  | 'CALL_GRAPH_DIRECTION_UNSPECIFIED'
  | 0
  | 'CALL_GRAPH_DIRECTION_OUT'
  | 1
  | 'CALL_GRAPH_DIRECTION_IN'
  | 2
  | 'CALL_GRAPH_DIRECTION_BOTH'
  | 3

export type CallGraphDirection__Output = typeof CallGraphDirection[keyof typeof CallGraphDirection]
