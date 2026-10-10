// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/batch.proto

import type { BatchGroup as _ctk_analysis_v1_BatchGroup, BatchGroup__Output as _ctk_analysis_v1_BatchGroup__Output } from '../../../ctk/analysis/v1/BatchGroup.js';
import type { StartBatchRequest as _ctk_analysis_v1_StartBatchRequest, StartBatchRequest__Output as _ctk_analysis_v1_StartBatchRequest__Output } from '../../../ctk/analysis/v1/StartBatchRequest.js';
import type { Long } from '@grpc/proto-loader';

export interface BatchRun {
  'runId'?: (string);
  'revision'?: (number | string | Long);
  'state'?: (string);
  'groups'?: (_ctk_analysis_v1_BatchGroup)[];
  'resultsComplete'?: (boolean);
  'peakAccountedBytes'?: (number | string | Long);
  'peakReservedBytes'?: (number | string | Long);
  'manifest'?: (_ctk_analysis_v1_StartBatchRequest | null);
}

export interface BatchRun__Output {
  'runId': (string);
  'revision': (string);
  'state': (string);
  'groups': (_ctk_analysis_v1_BatchGroup__Output)[];
  'resultsComplete': (boolean);
  'peakAccountedBytes': (string);
  'peakReservedBytes': (string);
  'manifest': (_ctk_analysis_v1_StartBatchRequest__Output | null);
}
