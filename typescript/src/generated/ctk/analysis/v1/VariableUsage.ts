// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/variable_flow.proto

import type { VariableFlowLocation as _ctk_analysis_v1_VariableFlowLocation, VariableFlowLocation__Output as _ctk_analysis_v1_VariableFlowLocation__Output } from '../../../ctk/analysis/v1/VariableFlowLocation.js';
import type { Long } from '@grpc/proto-loader';

// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/variable_flow.proto

export const _ctk_analysis_v1_VariableUsage_Kind = {
  KIND_UNSPECIFIED: 'KIND_UNSPECIFIED',
  DECLARE: 'DECLARE',
  INITIALIZE: 'INITIALIZE',
  READ: 'READ',
  WRITE: 'WRITE',
  READ_WRITE: 'READ_WRITE',
  ADDRESS_TAKEN: 'ADDRESS_TAKEN',
  UNKNOWN_EFFECT: 'UNKNOWN_EFFECT',
} as const;

export type _ctk_analysis_v1_VariableUsage_Kind =
  | 'KIND_UNSPECIFIED'
  | 0
  | 'DECLARE'
  | 1
  | 'INITIALIZE'
  | 2
  | 'READ'
  | 3
  | 'WRITE'
  | 4
  | 'READ_WRITE'
  | 5
  | 'ADDRESS_TAKEN'
  | 6
  | 'UNKNOWN_EFFECT'
  | 7

export type _ctk_analysis_v1_VariableUsage_Kind__Output = typeof _ctk_analysis_v1_VariableUsage_Kind[keyof typeof _ctk_analysis_v1_VariableUsage_Kind]

export interface VariableUsage {
  'id'?: (number | string | Long);
  'block'?: (number);
  'element'?: (number);
  'kind'?: (_ctk_analysis_v1_VariableUsage_Kind);
  'location'?: (_ctk_analysis_v1_VariableFlowLocation | null);
  'provisional'?: (boolean);
}

export interface VariableUsage__Output {
  'id': (string);
  'block': (number);
  'element': (number);
  'kind': (_ctk_analysis_v1_VariableUsage_Kind__Output);
  'location': (_ctk_analysis_v1_VariableFlowLocation__Output | null);
  'provisional': (boolean);
}
