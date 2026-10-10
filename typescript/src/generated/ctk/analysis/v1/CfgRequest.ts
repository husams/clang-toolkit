// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/cfg_request.proto

import type { FileMatchTarget as _ctk_match_v1_FileMatchTarget, FileMatchTarget__Output as _ctk_match_v1_FileMatchTarget__Output } from '../../../ctk/match/v1/FileMatchTarget.js';
import type { CfgOptions as _ctk_analysis_v1_CfgOptions, CfgOptions__Output as _ctk_analysis_v1_CfgOptions__Output } from '../../../ctk/analysis/v1/CfgOptions.js';
import type { ValueProjection as _ctk_analysis_v1_ValueProjection, ValueProjection__Output as _ctk_analysis_v1_ValueProjection__Output } from '../../../ctk/analysis/v1/ValueProjection.js';
import type { Long } from '@grpc/proto-loader';

export interface CfgRequest {
  'file'?: (_ctk_match_v1_FileMatchTarget | null);
  'function'?: (string);
  'options'?: (_ctk_analysis_v1_CfgOptions | null);
  'maxFunctions'?: (number | string | Long);
  'maxBlocks'?: (number | string | Long);
  'maxElements'?: (number | string | Long);
  'projection'?: (_ctk_analysis_v1_ValueProjection | null);
  'mainFileOnly'?: (boolean);
  'resourceScopeId'?: (string);
  '_maxFunctions'?: "maxFunctions";
  '_maxBlocks'?: "maxBlocks";
  '_maxElements'?: "maxElements";
}

export interface CfgRequest__Output {
  'file': (_ctk_match_v1_FileMatchTarget__Output | null);
  'function': (string);
  'options': (_ctk_analysis_v1_CfgOptions__Output | null);
  'maxFunctions'?: (string);
  'maxBlocks'?: (string);
  'maxElements'?: (string);
  'projection': (_ctk_analysis_v1_ValueProjection__Output | null);
  'mainFileOnly': (boolean);
  'resourceScopeId': (string);
  '_maxFunctions'?: "maxFunctions";
  '_maxBlocks'?: "maxBlocks";
  '_maxElements'?: "maxElements";
}
