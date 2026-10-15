// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/cfg_stream.proto

import type { CfgGraph as _ctk_analysis_v1_CfgGraph, CfgGraph__Output as _ctk_analysis_v1_CfgGraph__Output } from '../../../ctk/analysis/v1/CfgGraph.js';
import type { Long } from '@grpc/proto-loader';

export interface CfgGraphStarted {
  'graphIndex'?: (number | string | Long);
  'snapshotGeneration'?: (number | string | Long);
  'graph'?: (_ctk_analysis_v1_CfgGraph | null);
}

export interface CfgGraphStarted__Output {
  'graphIndex': (string);
  'snapshotGeneration': (string);
  'graph': (_ctk_analysis_v1_CfgGraph__Output | null);
}
