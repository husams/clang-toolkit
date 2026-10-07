// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/analysis_service.proto

import type * as grpc from '@grpc/grpc-js'
import type { MethodDefinition } from '@grpc/proto-loader'
import type { CallGraphRequest as _ctk_analysis_v1_CallGraphRequest, CallGraphRequest__Output as _ctk_analysis_v1_CallGraphRequest__Output } from '../../../ctk/analysis/v1/CallGraphRequest.js';
import type { CallGraphResponse as _ctk_analysis_v1_CallGraphResponse, CallGraphResponse__Output as _ctk_analysis_v1_CallGraphResponse__Output } from '../../../ctk/analysis/v1/CallGraphResponse.js';
import type { CfgRequest as _ctk_analysis_v1_CfgRequest, CfgRequest__Output as _ctk_analysis_v1_CfgRequest__Output } from '../../../ctk/analysis/v1/CfgRequest.js';
import type { CfgResponse as _ctk_analysis_v1_CfgResponse, CfgResponse__Output as _ctk_analysis_v1_CfgResponse__Output } from '../../../ctk/analysis/v1/CfgResponse.js';
import type { ScriptRequest as _ctk_analysis_v1_ScriptRequest, ScriptRequest__Output as _ctk_analysis_v1_ScriptRequest__Output } from '../../../ctk/analysis/v1/ScriptRequest.js';
import type { ScriptResponse as _ctk_analysis_v1_ScriptResponse, ScriptResponse__Output as _ctk_analysis_v1_ScriptResponse__Output } from '../../../ctk/analysis/v1/ScriptResponse.js';
import type { TraverseRequest as _ctk_analysis_v1_TraverseRequest, TraverseRequest__Output as _ctk_analysis_v1_TraverseRequest__Output } from '../../../ctk/analysis/v1/TraverseRequest.js';
import type { TraverseResponse as _ctk_analysis_v1_TraverseResponse, TraverseResponse__Output as _ctk_analysis_v1_TraverseResponse__Output } from '../../../ctk/analysis/v1/TraverseResponse.js';

export interface AnalysisServiceClient extends grpc.Client {
  CallGraph(argument: _ctk_analysis_v1_CallGraphRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_CallGraphResponse__Output>): grpc.ClientUnaryCall;
  CallGraph(argument: _ctk_analysis_v1_CallGraphRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_CallGraphResponse__Output>): grpc.ClientUnaryCall;
  CallGraph(argument: _ctk_analysis_v1_CallGraphRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_CallGraphResponse__Output>): grpc.ClientUnaryCall;
  CallGraph(argument: _ctk_analysis_v1_CallGraphRequest, callback: grpc.requestCallback<_ctk_analysis_v1_CallGraphResponse__Output>): grpc.ClientUnaryCall;
  callGraph(argument: _ctk_analysis_v1_CallGraphRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_CallGraphResponse__Output>): grpc.ClientUnaryCall;
  callGraph(argument: _ctk_analysis_v1_CallGraphRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_CallGraphResponse__Output>): grpc.ClientUnaryCall;
  callGraph(argument: _ctk_analysis_v1_CallGraphRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_CallGraphResponse__Output>): grpc.ClientUnaryCall;
  callGraph(argument: _ctk_analysis_v1_CallGraphRequest, callback: grpc.requestCallback<_ctk_analysis_v1_CallGraphResponse__Output>): grpc.ClientUnaryCall;
  
  Cfg(argument: _ctk_analysis_v1_CfgRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_CfgResponse__Output>): grpc.ClientUnaryCall;
  Cfg(argument: _ctk_analysis_v1_CfgRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_CfgResponse__Output>): grpc.ClientUnaryCall;
  Cfg(argument: _ctk_analysis_v1_CfgRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_CfgResponse__Output>): grpc.ClientUnaryCall;
  Cfg(argument: _ctk_analysis_v1_CfgRequest, callback: grpc.requestCallback<_ctk_analysis_v1_CfgResponse__Output>): grpc.ClientUnaryCall;
  cfg(argument: _ctk_analysis_v1_CfgRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_CfgResponse__Output>): grpc.ClientUnaryCall;
  cfg(argument: _ctk_analysis_v1_CfgRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_CfgResponse__Output>): grpc.ClientUnaryCall;
  cfg(argument: _ctk_analysis_v1_CfgRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_CfgResponse__Output>): grpc.ClientUnaryCall;
  cfg(argument: _ctk_analysis_v1_CfgRequest, callback: grpc.requestCallback<_ctk_analysis_v1_CfgResponse__Output>): grpc.ClientUnaryCall;
  
  RunScript(argument: _ctk_analysis_v1_ScriptRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_ScriptResponse__Output>): grpc.ClientUnaryCall;
  RunScript(argument: _ctk_analysis_v1_ScriptRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_ScriptResponse__Output>): grpc.ClientUnaryCall;
  RunScript(argument: _ctk_analysis_v1_ScriptRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_ScriptResponse__Output>): grpc.ClientUnaryCall;
  RunScript(argument: _ctk_analysis_v1_ScriptRequest, callback: grpc.requestCallback<_ctk_analysis_v1_ScriptResponse__Output>): grpc.ClientUnaryCall;
  runScript(argument: _ctk_analysis_v1_ScriptRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_ScriptResponse__Output>): grpc.ClientUnaryCall;
  runScript(argument: _ctk_analysis_v1_ScriptRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_ScriptResponse__Output>): grpc.ClientUnaryCall;
  runScript(argument: _ctk_analysis_v1_ScriptRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_ScriptResponse__Output>): grpc.ClientUnaryCall;
  runScript(argument: _ctk_analysis_v1_ScriptRequest, callback: grpc.requestCallback<_ctk_analysis_v1_ScriptResponse__Output>): grpc.ClientUnaryCall;
  
  Traverse(argument: _ctk_analysis_v1_TraverseRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_TraverseResponse__Output>): grpc.ClientUnaryCall;
  Traverse(argument: _ctk_analysis_v1_TraverseRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_TraverseResponse__Output>): grpc.ClientUnaryCall;
  Traverse(argument: _ctk_analysis_v1_TraverseRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_TraverseResponse__Output>): grpc.ClientUnaryCall;
  Traverse(argument: _ctk_analysis_v1_TraverseRequest, callback: grpc.requestCallback<_ctk_analysis_v1_TraverseResponse__Output>): grpc.ClientUnaryCall;
  traverse(argument: _ctk_analysis_v1_TraverseRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_TraverseResponse__Output>): grpc.ClientUnaryCall;
  traverse(argument: _ctk_analysis_v1_TraverseRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_TraverseResponse__Output>): grpc.ClientUnaryCall;
  traverse(argument: _ctk_analysis_v1_TraverseRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_TraverseResponse__Output>): grpc.ClientUnaryCall;
  traverse(argument: _ctk_analysis_v1_TraverseRequest, callback: grpc.requestCallback<_ctk_analysis_v1_TraverseResponse__Output>): grpc.ClientUnaryCall;
  
}

export interface AnalysisServiceHandlers extends grpc.UntypedServiceImplementation {
  CallGraph: grpc.handleUnaryCall<_ctk_analysis_v1_CallGraphRequest__Output, _ctk_analysis_v1_CallGraphResponse>;
  
  Cfg: grpc.handleUnaryCall<_ctk_analysis_v1_CfgRequest__Output, _ctk_analysis_v1_CfgResponse>;
  
  RunScript: grpc.handleUnaryCall<_ctk_analysis_v1_ScriptRequest__Output, _ctk_analysis_v1_ScriptResponse>;
  
  Traverse: grpc.handleUnaryCall<_ctk_analysis_v1_TraverseRequest__Output, _ctk_analysis_v1_TraverseResponse>;
  
}

export interface AnalysisServiceDefinition extends grpc.ServiceDefinition {
  CallGraph: MethodDefinition<_ctk_analysis_v1_CallGraphRequest, _ctk_analysis_v1_CallGraphResponse, _ctk_analysis_v1_CallGraphRequest__Output, _ctk_analysis_v1_CallGraphResponse__Output>
  Cfg: MethodDefinition<_ctk_analysis_v1_CfgRequest, _ctk_analysis_v1_CfgResponse, _ctk_analysis_v1_CfgRequest__Output, _ctk_analysis_v1_CfgResponse__Output>
  RunScript: MethodDefinition<_ctk_analysis_v1_ScriptRequest, _ctk_analysis_v1_ScriptResponse, _ctk_analysis_v1_ScriptRequest__Output, _ctk_analysis_v1_ScriptResponse__Output>
  Traverse: MethodDefinition<_ctk_analysis_v1_TraverseRequest, _ctk_analysis_v1_TraverseResponse, _ctk_analysis_v1_TraverseRequest__Output, _ctk_analysis_v1_TraverseResponse__Output>
}
