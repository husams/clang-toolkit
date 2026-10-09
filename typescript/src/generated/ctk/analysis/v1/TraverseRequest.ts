// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/traverse_request.proto

import type { FileMatchTarget as _ctk_match_v1_FileMatchTarget, FileMatchTarget__Output as _ctk_match_v1_FileMatchTarget__Output } from '../../../ctk/match/v1/FileMatchTarget.js';
import type { ValueProjection as _ctk_analysis_v1_ValueProjection, ValueProjection__Output as _ctk_analysis_v1_ValueProjection__Output } from '../../../ctk/analysis/v1/ValueProjection.js';
import type { Long } from '@grpc/proto-loader';

export interface TraverseRequest {
  'file'?: (_ctk_match_v1_FileMatchTarget | null);
  'visitImplicitCode'?: (boolean);
  'visitTemplateInstantiations'?: (boolean);
  'maxDepth'?: (number);
  'maxNodes'?: (number | string | Long);
  'projection'?: (_ctk_analysis_v1_ValueProjection | null);
  'mainFileOnly'?: (boolean);
  '_maxDepth'?: "maxDepth";
  '_maxNodes'?: "maxNodes";
}

export interface TraverseRequest__Output {
  'file': (_ctk_match_v1_FileMatchTarget__Output | null);
  'visitImplicitCode': (boolean);
  'visitTemplateInstantiations': (boolean);
  'maxDepth'?: (number);
  'maxNodes'?: (string);
  'projection': (_ctk_analysis_v1_ValueProjection__Output | null);
  'mainFileOnly': (boolean);
  '_maxDepth'?: "maxDepth";
  '_maxNodes'?: "maxNodes";
}
