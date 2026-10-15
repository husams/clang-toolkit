// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/traverse_request.proto

import type { FileMatchTarget as _ctk_match_v1_FileMatchTarget, FileMatchTarget__Output as _ctk_match_v1_FileMatchTarget__Output } from '../../../ctk/match/v1/FileMatchTarget.js';
import type { ValueProjection as _ctk_analysis_v1_ValueProjection, ValueProjection__Output as _ctk_analysis_v1_ValueProjection__Output } from '../../../ctk/analysis/v1/ValueProjection.js';
import type { SessionMatchTarget as _ctk_match_v1_SessionMatchTarget, SessionMatchTarget__Output as _ctk_match_v1_SessionMatchTarget__Output } from '../../../ctk/match/v1/SessionMatchTarget.js';
import type { BindingMatchTarget as _ctk_match_v1_BindingMatchTarget, BindingMatchTarget__Output as _ctk_match_v1_BindingMatchTarget__Output } from '../../../ctk/match/v1/BindingMatchTarget.js';
import type { FileHandleTarget as _ctk_match_v1_FileHandleTarget, FileHandleTarget__Output as _ctk_match_v1_FileHandleTarget__Output } from '../../../ctk/match/v1/FileHandleTarget.js';
import type { Long } from '@grpc/proto-loader';

export interface TraverseRequest {
  'file'?: (_ctk_match_v1_FileMatchTarget | null);
  'visitImplicitCode'?: (boolean);
  'visitTemplateInstantiations'?: (boolean);
  'maxDepth'?: (number);
  'maxNodes'?: (number | string | Long);
  'projection'?: (_ctk_analysis_v1_ValueProjection | null);
  'mainFileOnly'?: (boolean);
  'resourceScopeId'?: (string);
  'session'?: (_ctk_match_v1_SessionMatchTarget | null);
  'binding'?: (_ctk_match_v1_BindingMatchTarget | null);
  'fileHandle'?: (_ctk_match_v1_FileHandleTarget | null);
  'target'?: "file"|"session"|"binding"|"fileHandle";
  '_maxDepth'?: "maxDepth";
  '_maxNodes'?: "maxNodes";
}

export interface TraverseRequest__Output {
  'file'?: (_ctk_match_v1_FileMatchTarget__Output | null);
  'visitImplicitCode': (boolean);
  'visitTemplateInstantiations': (boolean);
  'maxDepth'?: (number);
  'maxNodes'?: (string);
  'projection': (_ctk_analysis_v1_ValueProjection__Output | null);
  'mainFileOnly': (boolean);
  'resourceScopeId': (string);
  'session'?: (_ctk_match_v1_SessionMatchTarget__Output | null);
  'binding'?: (_ctk_match_v1_BindingMatchTarget__Output | null);
  'fileHandle'?: (_ctk_match_v1_FileHandleTarget__Output | null);
  'target'?: "file"|"session"|"binding"|"fileHandle";
  '_maxDepth'?: "maxDepth";
  '_maxNodes'?: "maxNodes";
}
