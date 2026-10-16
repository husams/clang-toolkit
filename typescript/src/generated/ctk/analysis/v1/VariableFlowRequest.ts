// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/variable_flow.proto

import type { BindingMatchTarget as _ctk_match_v1_BindingMatchTarget, BindingMatchTarget__Output as _ctk_match_v1_BindingMatchTarget__Output } from '../../../ctk/match/v1/BindingMatchTarget.js';
import type { VariableValueDomain as _ctk_analysis_v1_VariableValueDomain, VariableValueDomain__Output as _ctk_analysis_v1_VariableValueDomain__Output } from '../../../ctk/analysis/v1/VariableValueDomain.js';

export interface VariableFlowRequest {
  'variable'?: (_ctk_match_v1_BindingMatchTarget | null);
  'function'?: (_ctk_match_v1_BindingMatchTarget | null);
  'resourceScopeId'?: (string);
  'maxBlocks'?: (number);
  'maxEvents'?: (number);
  'maxIterations'?: (number);
  'valueDomain'?: (_ctk_analysis_v1_VariableValueDomain);
  '_maxBlocks'?: "maxBlocks";
  '_maxEvents'?: "maxEvents";
  '_maxIterations'?: "maxIterations";
}

export interface VariableFlowRequest__Output {
  'variable': (_ctk_match_v1_BindingMatchTarget__Output | null);
  'function': (_ctk_match_v1_BindingMatchTarget__Output | null);
  'resourceScopeId': (string);
  'maxBlocks'?: (number);
  'maxEvents'?: (number);
  'maxIterations'?: (number);
  'valueDomain': (_ctk_analysis_v1_VariableValueDomain__Output);
  '_maxBlocks'?: "maxBlocks";
  '_maxEvents'?: "maxEvents";
  '_maxIterations'?: "maxIterations";
}
