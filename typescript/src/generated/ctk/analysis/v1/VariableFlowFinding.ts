// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/variable_flow.proto

import type { Long } from '@grpc/proto-loader';

// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/variable_flow.proto

export const _ctk_analysis_v1_VariableFlowFinding_Kind = {
  KIND_UNSPECIFIED: 'KIND_UNSPECIFIED',
  POSSIBLY_UNINITIALIZED: 'POSSIBLY_UNINITIALIZED',
  UNINITIALIZED_READ: 'UNINITIALIZED_READ',
  DEAD_STORE: 'DEAD_STORE',
  UNSUPPORTED_EFFECT: 'UNSUPPORTED_EFFECT',
} as const;

export type _ctk_analysis_v1_VariableFlowFinding_Kind =
  | 'KIND_UNSPECIFIED'
  | 0
  | 'POSSIBLY_UNINITIALIZED'
  | 1
  | 'UNINITIALIZED_READ'
  | 2
  | 'DEAD_STORE'
  | 3
  | 'UNSUPPORTED_EFFECT'
  | 4

export type _ctk_analysis_v1_VariableFlowFinding_Kind__Output = typeof _ctk_analysis_v1_VariableFlowFinding_Kind[keyof typeof _ctk_analysis_v1_VariableFlowFinding_Kind]

export interface VariableFlowFinding {
  'kind'?: (_ctk_analysis_v1_VariableFlowFinding_Kind);
  'usageId'?: (number | string | Long);
  'message'?: (string);
  'witnessBlocks'?: (number)[];
}

export interface VariableFlowFinding__Output {
  'kind': (_ctk_analysis_v1_VariableFlowFinding_Kind__Output);
  'usageId': (string);
  'message': (string);
  'witnessBlocks': (number)[];
}
