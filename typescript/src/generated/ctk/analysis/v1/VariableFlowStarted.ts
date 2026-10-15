// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/variable_flow.proto

import type { VariableFlowLocation as _ctk_analysis_v1_VariableFlowLocation, VariableFlowLocation__Output as _ctk_analysis_v1_VariableFlowLocation__Output } from '../../../ctk/analysis/v1/VariableFlowLocation.js';
import type { Long } from '@grpc/proto-loader';

export interface VariableFlowStarted {
  'variable'?: (string);
  'function'?: (string);
  'snapshotGeneration'?: (number | string | Long);
  'declarationId'?: (number | string | Long);
  'declaration'?: (_ctk_analysis_v1_VariableFlowLocation | null);
  'entryBlock'?: (number);
  'exitBlock'?: (number);
}

export interface VariableFlowStarted__Output {
  'variable': (string);
  'function': (string);
  'snapshotGeneration': (string);
  'declarationId': (string);
  'declaration': (_ctk_analysis_v1_VariableFlowLocation__Output | null);
  'entryBlock': (number);
  'exitBlock': (number);
}
