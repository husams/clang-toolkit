// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/cfg_stream.proto

import type { CfgBlock as _ctk_analysis_v1_CfgBlock, CfgBlock__Output as _ctk_analysis_v1_CfgBlock__Output } from '../../../ctk/analysis/v1/CfgBlock.js';
import type { Long } from '@grpc/proto-loader';

export interface CfgBlockEvent {
  'graphIndex'?: (number | string | Long);
  'block'?: (_ctk_analysis_v1_CfgBlock | null);
}

export interface CfgBlockEvent__Output {
  'graphIndex': (string);
  'block': (_ctk_analysis_v1_CfgBlock__Output | null);
}
