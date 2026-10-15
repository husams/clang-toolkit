// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/variable_flow.proto

import type { BindingMatchTarget as _ctk_match_v1_BindingMatchTarget, BindingMatchTarget__Output as _ctk_match_v1_BindingMatchTarget__Output } from '../../../ctk/match/v1/BindingMatchTarget.js';

export interface VariableFlowRequest {
  'variable'?: (_ctk_match_v1_BindingMatchTarget | null);
  'function'?: (_ctk_match_v1_BindingMatchTarget | null);
  'resourceScopeId'?: (string);
  'maxBlocks'?: (number);
  'maxEvents'?: (number);
  'maxIterations'?: (number);
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
  '_maxBlocks'?: "maxBlocks";
  '_maxEvents'?: "maxEvents";
  '_maxIterations'?: "maxIterations";
}
