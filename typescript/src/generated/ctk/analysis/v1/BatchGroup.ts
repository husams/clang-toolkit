// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/batch.proto

import type { InputDescriptor as _ctk_match_v1_InputDescriptor, InputDescriptor__Output as _ctk_match_v1_InputDescriptor__Output } from '../../../ctk/match/v1/InputDescriptor.js';
import type { ScriptResponse as _ctk_analysis_v1_ScriptResponse, ScriptResponse__Output as _ctk_analysis_v1_ScriptResponse__Output } from '../../../ctk/analysis/v1/ScriptResponse.js';
import type { BatchExport as _ctk_analysis_v1_BatchExport, BatchExport__Output as _ctk_analysis_v1_BatchExport__Output } from '../../../ctk/analysis/v1/BatchExport.js';

export interface BatchGroup {
  'index'?: (number);
  'inputs'?: (_ctk_match_v1_InputDescriptor)[];
  'sourceRevisions'?: (string)[];
  'state'?: (string);
  'message'?: (string);
  'resourceScopeId'?: (string);
  'cleanupAcknowledged'?: (boolean);
  'result'?: (_ctk_analysis_v1_ScriptResponse | null);
  'exports'?: (_ctk_analysis_v1_BatchExport)[];
}

export interface BatchGroup__Output {
  'index': (number);
  'inputs': (_ctk_match_v1_InputDescriptor__Output)[];
  'sourceRevisions': (string)[];
  'state': (string);
  'message': (string);
  'resourceScopeId': (string);
  'cleanupAcknowledged': (boolean);
  'result': (_ctk_analysis_v1_ScriptResponse__Output | null);
  'exports': (_ctk_analysis_v1_BatchExport__Output)[];
}
