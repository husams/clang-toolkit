// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/traverse_request.proto

import type { FileMatchTarget as _ctk_match_v1_FileMatchTarget, FileMatchTarget__Output as _ctk_match_v1_FileMatchTarget__Output } from '../../../ctk/match/v1/FileMatchTarget.js';
import type { Long } from '@grpc/proto-loader';

export interface TraverseRequest {
  'file'?: (_ctk_match_v1_FileMatchTarget | null);
  'visitImplicitCode'?: (boolean);
  'visitTemplateInstantiations'?: (boolean);
  'maxDepth'?: (number);
  'maxNodes'?: (number | string | Long);
  '_maxDepth'?: "maxDepth";
  '_maxNodes'?: "maxNodes";
}

export interface TraverseRequest__Output {
  'file': (_ctk_match_v1_FileMatchTarget__Output | null);
  'visitImplicitCode': (boolean);
  'visitTemplateInstantiations': (boolean);
  'maxDepth'?: (number);
  'maxNodes'?: (string);
  '_maxDepth'?: "maxDepth";
  '_maxNodes'?: "maxNodes";
}
