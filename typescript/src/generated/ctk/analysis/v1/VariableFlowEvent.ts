// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/variable_flow.proto

import type { VariableFlowStarted as _ctk_analysis_v1_VariableFlowStarted, VariableFlowStarted__Output as _ctk_analysis_v1_VariableFlowStarted__Output } from '../../../ctk/analysis/v1/VariableFlowStarted.js';
import type { VariableUsage as _ctk_analysis_v1_VariableUsage, VariableUsage__Output as _ctk_analysis_v1_VariableUsage__Output } from '../../../ctk/analysis/v1/VariableUsage.js';
import type { VariableFlowFact as _ctk_analysis_v1_VariableFlowFact, VariableFlowFact__Output as _ctk_analysis_v1_VariableFlowFact__Output } from '../../../ctk/analysis/v1/VariableFlowFact.js';
import type { VariableFlowFinding as _ctk_analysis_v1_VariableFlowFinding, VariableFlowFinding__Output as _ctk_analysis_v1_VariableFlowFinding__Output } from '../../../ctk/analysis/v1/VariableFlowFinding.js';
import type { VariableFlowCompleted as _ctk_analysis_v1_VariableFlowCompleted, VariableFlowCompleted__Output as _ctk_analysis_v1_VariableFlowCompleted__Output } from '../../../ctk/analysis/v1/VariableFlowCompleted.js';

export interface VariableFlowEvent {
  'started'?: (_ctk_analysis_v1_VariableFlowStarted | null);
  'usage'?: (_ctk_analysis_v1_VariableUsage | null);
  'fact'?: (_ctk_analysis_v1_VariableFlowFact | null);
  'finding'?: (_ctk_analysis_v1_VariableFlowFinding | null);
  'completed'?: (_ctk_analysis_v1_VariableFlowCompleted | null);
  'event'?: "started"|"usage"|"fact"|"finding"|"completed";
}

export interface VariableFlowEvent__Output {
  'started'?: (_ctk_analysis_v1_VariableFlowStarted__Output | null);
  'usage'?: (_ctk_analysis_v1_VariableUsage__Output | null);
  'fact'?: (_ctk_analysis_v1_VariableFlowFact__Output | null);
  'finding'?: (_ctk_analysis_v1_VariableFlowFinding__Output | null);
  'completed'?: (_ctk_analysis_v1_VariableFlowCompleted__Output | null);
  'event'?: "started"|"usage"|"fact"|"finding"|"completed";
}
