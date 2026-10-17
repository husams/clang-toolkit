// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/variable_flow.proto

import type { VariableFlowStarted as _ctk_analysis_v1_VariableFlowStarted, VariableFlowStarted__Output as _ctk_analysis_v1_VariableFlowStarted__Output } from '../../../ctk/analysis/v1/VariableFlowStarted.js';
import type { VariableUsage as _ctk_analysis_v1_VariableUsage, VariableUsage__Output as _ctk_analysis_v1_VariableUsage__Output } from '../../../ctk/analysis/v1/VariableUsage.js';
import type { VariableFlowFact as _ctk_analysis_v1_VariableFlowFact, VariableFlowFact__Output as _ctk_analysis_v1_VariableFlowFact__Output } from '../../../ctk/analysis/v1/VariableFlowFact.js';
import type { VariableFlowFinding as _ctk_analysis_v1_VariableFlowFinding, VariableFlowFinding__Output as _ctk_analysis_v1_VariableFlowFinding__Output } from '../../../ctk/analysis/v1/VariableFlowFinding.js';
import type { VariableFlowCompleted as _ctk_analysis_v1_VariableFlowCompleted, VariableFlowCompleted__Output as _ctk_analysis_v1_VariableFlowCompleted__Output } from '../../../ctk/analysis/v1/VariableFlowCompleted.js';

export interface VariableFlowReport {
  'analysis'?: (_ctk_analysis_v1_VariableFlowStarted | null);
  'usages'?: (_ctk_analysis_v1_VariableUsage)[];
  'facts'?: (_ctk_analysis_v1_VariableFlowFact)[];
  'findings'?: (_ctk_analysis_v1_VariableFlowFinding)[];
  'completed'?: (_ctk_analysis_v1_VariableFlowCompleted | null);
}

export interface VariableFlowReport__Output {
  'analysis': (_ctk_analysis_v1_VariableFlowStarted__Output | null);
  'usages': (_ctk_analysis_v1_VariableUsage__Output)[];
  'facts': (_ctk_analysis_v1_VariableFlowFact__Output)[];
  'findings': (_ctk_analysis_v1_VariableFlowFinding__Output)[];
  'completed': (_ctk_analysis_v1_VariableFlowCompleted__Output | null);
}
