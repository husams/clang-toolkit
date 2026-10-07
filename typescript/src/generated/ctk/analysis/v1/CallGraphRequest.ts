// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/call_graph_request.proto

import type { FileMatchTarget as _ctk_match_v1_FileMatchTarget, FileMatchTarget__Output as _ctk_match_v1_FileMatchTarget__Output } from '../../../ctk/match/v1/FileMatchTarget.js';
import type { Long } from '@grpc/proto-loader';

export interface CallGraphRequest {
  'file'?: (_ctk_match_v1_FileMatchTarget | null);
  'visitImplicitCode'?: (boolean);
  'visitTemplateInstantiations'?: (boolean);
  'maxNodes'?: (number | string | Long);
  'maxEdges'?: (number | string | Long);
  '_visitImplicitCode'?: "visitImplicitCode";
  '_visitTemplateInstantiations'?: "visitTemplateInstantiations";
  '_maxNodes'?: "maxNodes";
  '_maxEdges'?: "maxEdges";
}

export interface CallGraphRequest__Output {
  'file': (_ctk_match_v1_FileMatchTarget__Output | null);
  'visitImplicitCode'?: (boolean);
  'visitTemplateInstantiations'?: (boolean);
  'maxNodes'?: (string);
  'maxEdges'?: (string);
  '_visitImplicitCode'?: "visitImplicitCode";
  '_visitTemplateInstantiations'?: "visitTemplateInstantiations";
  '_maxNodes'?: "maxNodes";
  '_maxEdges'?: "maxEdges";
}
