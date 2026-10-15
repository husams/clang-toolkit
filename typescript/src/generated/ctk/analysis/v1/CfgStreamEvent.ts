// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/cfg_stream.proto

import type { CfgGraphStarted as _ctk_analysis_v1_CfgGraphStarted, CfgGraphStarted__Output as _ctk_analysis_v1_CfgGraphStarted__Output } from '../../../ctk/analysis/v1/CfgGraphStarted.js';
import type { CfgBlockEvent as _ctk_analysis_v1_CfgBlockEvent, CfgBlockEvent__Output as _ctk_analysis_v1_CfgBlockEvent__Output } from '../../../ctk/analysis/v1/CfgBlockEvent.js';
import type { CfgGraphCompleted as _ctk_analysis_v1_CfgGraphCompleted, CfgGraphCompleted__Output as _ctk_analysis_v1_CfgGraphCompleted__Output } from '../../../ctk/analysis/v1/CfgGraphCompleted.js';
import type { CfgCompleted as _ctk_analysis_v1_CfgCompleted, CfgCompleted__Output as _ctk_analysis_v1_CfgCompleted__Output } from '../../../ctk/analysis/v1/CfgCompleted.js';

export interface CfgStreamEvent {
  'graphStarted'?: (_ctk_analysis_v1_CfgGraphStarted | null);
  'block'?: (_ctk_analysis_v1_CfgBlockEvent | null);
  'graphCompleted'?: (_ctk_analysis_v1_CfgGraphCompleted | null);
  'completed'?: (_ctk_analysis_v1_CfgCompleted | null);
  'event'?: "graphStarted"|"block"|"graphCompleted"|"completed";
}

export interface CfgStreamEvent__Output {
  'graphStarted'?: (_ctk_analysis_v1_CfgGraphStarted__Output | null);
  'block'?: (_ctk_analysis_v1_CfgBlockEvent__Output | null);
  'graphCompleted'?: (_ctk_analysis_v1_CfgGraphCompleted__Output | null);
  'completed'?: (_ctk_analysis_v1_CfgCompleted__Output | null);
  'event'?: "graphStarted"|"block"|"graphCompleted"|"completed";
}
