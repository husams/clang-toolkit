// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/script_response.proto

import type { ScriptEmission as _ctk_analysis_v1_ScriptEmission, ScriptEmission__Output as _ctk_analysis_v1_ScriptEmission__Output } from '../../../ctk/analysis/v1/ScriptEmission.js';

export interface ScriptResponse {
  'emissions'?: (_ctk_analysis_v1_ScriptEmission)[];
  'executedSteps'?: (number);
}

export interface ScriptResponse__Output {
  'emissions': (_ctk_analysis_v1_ScriptEmission__Output)[];
  'executedSteps': (number);
}
