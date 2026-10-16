// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/variable_flow.proto

import type { VariableValueRange as _ctk_analysis_v1_VariableValueRange, VariableValueRange__Output as _ctk_analysis_v1_VariableValueRange__Output } from '../../../ctk/analysis/v1/VariableValueRange.js';
import type { Long } from '@grpc/proto-loader';

// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/variable_flow.proto

export const _ctk_analysis_v1_VariableFlowFact_Initialization = {
  INITIALIZATION_UNSPECIFIED: 'INITIALIZATION_UNSPECIFIED',
  UNINITIALIZED: 'UNINITIALIZED',
  MAYBE_INITIALIZED: 'MAYBE_INITIALIZED',
  INITIALIZED: 'INITIALIZED',
  UNKNOWN: 'UNKNOWN',
} as const;

export type _ctk_analysis_v1_VariableFlowFact_Initialization =
  | 'INITIALIZATION_UNSPECIFIED'
  | 0
  | 'UNINITIALIZED'
  | 1
  | 'MAYBE_INITIALIZED'
  | 2
  | 'INITIALIZED'
  | 3
  | 'UNKNOWN'
  | 4

export type _ctk_analysis_v1_VariableFlowFact_Initialization__Output = typeof _ctk_analysis_v1_VariableFlowFact_Initialization[keyof typeof _ctk_analysis_v1_VariableFlowFact_Initialization]

export interface VariableFlowFact {
  'usageId'?: (number | string | Long);
  'reachable'?: (boolean);
  'initialization'?: (_ctk_analysis_v1_VariableFlowFact_Initialization);
  'reachingAssignments'?: (number | string | Long)[];
  'liveAfter'?: (boolean);
  'deadStore'?: (boolean);
  'valueBefore'?: (_ctk_analysis_v1_VariableValueRange | null);
  'valueAfter'?: (_ctk_analysis_v1_VariableValueRange | null);
}

export interface VariableFlowFact__Output {
  'usageId': (string);
  'reachable': (boolean);
  'initialization': (_ctk_analysis_v1_VariableFlowFact_Initialization__Output);
  'reachingAssignments': (string)[];
  'liveAfter': (boolean);
  'deadStore': (boolean);
  'valueBefore': (_ctk_analysis_v1_VariableValueRange__Output | null);
  'valueAfter': (_ctk_analysis_v1_VariableValueRange__Output | null);
}
