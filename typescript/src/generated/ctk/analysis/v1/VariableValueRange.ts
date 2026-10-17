// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/variable_flow.proto


// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/variable_flow.proto

export const _ctk_analysis_v1_VariableValueRange_Kind = {
  KIND_UNSPECIFIED: 'KIND_UNSPECIFIED',
  INTERVAL: 'INTERVAL',
  UNINITIALIZED: 'UNINITIALIZED',
  UNREACHABLE: 'UNREACHABLE',
  UNKNOWN: 'UNKNOWN',
} as const;

export type _ctk_analysis_v1_VariableValueRange_Kind =
  | 'KIND_UNSPECIFIED'
  | 0
  | 'INTERVAL'
  | 1
  | 'UNINITIALIZED'
  | 2
  | 'UNREACHABLE'
  | 3
  | 'UNKNOWN'
  | 4

export type _ctk_analysis_v1_VariableValueRange_Kind__Output = typeof _ctk_analysis_v1_VariableValueRange_Kind[keyof typeof _ctk_analysis_v1_VariableValueRange_Kind]

export interface VariableValueRange {
  'kind'?: (_ctk_analysis_v1_VariableValueRange_Kind);
  'lower'?: (string);
  'upper'?: (string);
}

export interface VariableValueRange__Output {
  'kind': (_ctk_analysis_v1_VariableValueRange_Kind__Output);
  'lower': (string);
  'upper': (string);
}
