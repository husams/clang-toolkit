// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/call_graph_request.proto

import type { FileMatchTarget as _ctk_match_v1_FileMatchTarget, FileMatchTarget__Output as _ctk_match_v1_FileMatchTarget__Output } from '../../../ctk/match/v1/FileMatchTarget.js';
import type { ValueProjection as _ctk_analysis_v1_ValueProjection, ValueProjection__Output as _ctk_analysis_v1_ValueProjection__Output } from '../../../ctk/analysis/v1/ValueProjection.js';
import type { SessionMatchTarget as _ctk_match_v1_SessionMatchTarget, SessionMatchTarget__Output as _ctk_match_v1_SessionMatchTarget__Output } from '../../../ctk/match/v1/SessionMatchTarget.js';
import type { BindingMatchTarget as _ctk_match_v1_BindingMatchTarget, BindingMatchTarget__Output as _ctk_match_v1_BindingMatchTarget__Output } from '../../../ctk/match/v1/BindingMatchTarget.js';
import type { FileHandleTarget as _ctk_match_v1_FileHandleTarget, FileHandleTarget__Output as _ctk_match_v1_FileHandleTarget__Output } from '../../../ctk/match/v1/FileHandleTarget.js';
import type { CallGraphDirection as _ctk_analysis_v1_CallGraphDirection, CallGraphDirection__Output as _ctk_analysis_v1_CallGraphDirection__Output } from '../../../ctk/analysis/v1/CallGraphDirection.js';
import type { Long } from '@grpc/proto-loader';

export interface CallGraphRequest {
  'file'?: (_ctk_match_v1_FileMatchTarget | null);
  'visitImplicitCode'?: (boolean);
  'visitTemplateInstantiations'?: (boolean);
  'maxNodes'?: (number | string | Long);
  'maxEdges'?: (number | string | Long);
  'projection'?: (_ctk_analysis_v1_ValueProjection | null);
  'mainFileOnly'?: (boolean);
  'resourceScopeId'?: (string);
  'session'?: (_ctk_match_v1_SessionMatchTarget | null);
  'binding'?: (_ctk_match_v1_BindingMatchTarget | null);
  'fileHandle'?: (_ctk_match_v1_FileHandleTarget | null);
  'direction'?: (_ctk_analysis_v1_CallGraphDirection);
  'maxDepth'?: (number | string | Long);
  'maxCallSites'?: (number | string | Long);
  'function'?: (string);
  'target'?: "file"|"session"|"binding"|"fileHandle";
  '_visitImplicitCode'?: "visitImplicitCode";
  '_visitTemplateInstantiations'?: "visitTemplateInstantiations";
  '_maxNodes'?: "maxNodes";
  '_maxEdges'?: "maxEdges";
  '_maxDepth'?: "maxDepth";
  '_maxCallSites'?: "maxCallSites";
}

export interface CallGraphRequest__Output {
  'file'?: (_ctk_match_v1_FileMatchTarget__Output | null);
  'visitImplicitCode'?: (boolean);
  'visitTemplateInstantiations'?: (boolean);
  'maxNodes'?: (string);
  'maxEdges'?: (string);
  'projection': (_ctk_analysis_v1_ValueProjection__Output | null);
  'mainFileOnly': (boolean);
  'resourceScopeId': (string);
  'session'?: (_ctk_match_v1_SessionMatchTarget__Output | null);
  'binding'?: (_ctk_match_v1_BindingMatchTarget__Output | null);
  'fileHandle'?: (_ctk_match_v1_FileHandleTarget__Output | null);
  'direction': (_ctk_analysis_v1_CallGraphDirection__Output);
  'maxDepth'?: (string);
  'maxCallSites'?: (string);
  'function': (string);
  'target'?: "file"|"session"|"binding"|"fileHandle";
  '_visitImplicitCode'?: "visitImplicitCode";
  '_visitTemplateInstantiations'?: "visitTemplateInstantiations";
  '_maxNodes'?: "maxNodes";
  '_maxEdges'?: "maxEdges";
  '_maxDepth'?: "maxDepth";
  '_maxCallSites'?: "maxCallSites";
}
