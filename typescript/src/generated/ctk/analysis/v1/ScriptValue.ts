// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/script_value.proto

import type { ScriptScalar as _ctk_analysis_v1_ScriptScalar, ScriptScalar__Output as _ctk_analysis_v1_ScriptScalar__Output } from '../../../ctk/analysis/v1/ScriptScalar.js';
import type { ScriptMatchRows as _ctk_analysis_v1_ScriptMatchRows, ScriptMatchRows__Output as _ctk_analysis_v1_ScriptMatchRows__Output } from '../../../ctk/analysis/v1/ScriptMatchRows.js';
import type { TraverseResponse as _ctk_analysis_v1_TraverseResponse, TraverseResponse__Output as _ctk_analysis_v1_TraverseResponse__Output } from '../../../ctk/analysis/v1/TraverseResponse.js';
import type { CfgResponse as _ctk_analysis_v1_CfgResponse, CfgResponse__Output as _ctk_analysis_v1_CfgResponse__Output } from '../../../ctk/analysis/v1/CfgResponse.js';
import type { CallGraphResponse as _ctk_analysis_v1_CallGraphResponse, CallGraphResponse__Output as _ctk_analysis_v1_CallGraphResponse__Output } from '../../../ctk/analysis/v1/CallGraphResponse.js';
import type { ScriptTree as _ctk_analysis_v1_ScriptTree, ScriptTree__Output as _ctk_analysis_v1_ScriptTree__Output } from '../../../ctk/analysis/v1/ScriptTree.js';

export interface ScriptValue {
  'scalar'?: (_ctk_analysis_v1_ScriptScalar | null);
  'matches'?: (_ctk_analysis_v1_ScriptMatchRows | null);
  'traversal'?: (_ctk_analysis_v1_TraverseResponse | null);
  'cfg'?: (_ctk_analysis_v1_CfgResponse | null);
  'callGraph'?: (_ctk_analysis_v1_CallGraphResponse | null);
  'tree'?: (_ctk_analysis_v1_ScriptTree | null);
  'value'?: "scalar"|"matches"|"traversal"|"cfg"|"callGraph"|"tree";
}

export interface ScriptValue__Output {
  'scalar'?: (_ctk_analysis_v1_ScriptScalar__Output | null);
  'matches'?: (_ctk_analysis_v1_ScriptMatchRows__Output | null);
  'traversal'?: (_ctk_analysis_v1_TraverseResponse__Output | null);
  'cfg'?: (_ctk_analysis_v1_CfgResponse__Output | null);
  'callGraph'?: (_ctk_analysis_v1_CallGraphResponse__Output | null);
  'tree'?: (_ctk_analysis_v1_ScriptTree__Output | null);
  'value'?: "scalar"|"matches"|"traversal"|"cfg"|"callGraph"|"tree";
}
