// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/analysis_service.proto

import type * as grpc from '@grpc/grpc-js'
import type { MethodDefinition } from '@grpc/proto-loader'
import type { BatchControlRequest as _ctk_analysis_v1_BatchControlRequest, BatchControlRequest__Output as _ctk_analysis_v1_BatchControlRequest__Output } from '../../../ctk/analysis/v1/BatchControlRequest.js';
import type { BatchRun as _ctk_analysis_v1_BatchRun, BatchRun__Output as _ctk_analysis_v1_BatchRun__Output } from '../../../ctk/analysis/v1/BatchRun.js';
import type { BatchRunRequest as _ctk_analysis_v1_BatchRunRequest, BatchRunRequest__Output as _ctk_analysis_v1_BatchRunRequest__Output } from '../../../ctk/analysis/v1/BatchRunRequest.js';
import type { CallGraphRequest as _ctk_analysis_v1_CallGraphRequest, CallGraphRequest__Output as _ctk_analysis_v1_CallGraphRequest__Output } from '../../../ctk/analysis/v1/CallGraphRequest.js';
import type { CallGraphResponse as _ctk_analysis_v1_CallGraphResponse, CallGraphResponse__Output as _ctk_analysis_v1_CallGraphResponse__Output } from '../../../ctk/analysis/v1/CallGraphResponse.js';
import type { CfgRequest as _ctk_analysis_v1_CfgRequest, CfgRequest__Output as _ctk_analysis_v1_CfgRequest__Output } from '../../../ctk/analysis/v1/CfgRequest.js';
import type { CfgResponse as _ctk_analysis_v1_CfgResponse, CfgResponse__Output as _ctk_analysis_v1_CfgResponse__Output } from '../../../ctk/analysis/v1/CfgResponse.js';
import type { ScriptRequest as _ctk_analysis_v1_ScriptRequest, ScriptRequest__Output as _ctk_analysis_v1_ScriptRequest__Output } from '../../../ctk/analysis/v1/ScriptRequest.js';
import type { ScriptResponse as _ctk_analysis_v1_ScriptResponse, ScriptResponse__Output as _ctk_analysis_v1_ScriptResponse__Output } from '../../../ctk/analysis/v1/ScriptResponse.js';
import type { StartBatchRequest as _ctk_analysis_v1_StartBatchRequest, StartBatchRequest__Output as _ctk_analysis_v1_StartBatchRequest__Output } from '../../../ctk/analysis/v1/StartBatchRequest.js';
import type { TraverseRequest as _ctk_analysis_v1_TraverseRequest, TraverseRequest__Output as _ctk_analysis_v1_TraverseRequest__Output } from '../../../ctk/analysis/v1/TraverseRequest.js';
import type { TraverseResponse as _ctk_analysis_v1_TraverseResponse, TraverseResponse__Output as _ctk_analysis_v1_TraverseResponse__Output } from '../../../ctk/analysis/v1/TraverseResponse.js';

export interface AnalysisServiceClient extends grpc.Client {
  BatchStatus(argument: _ctk_analysis_v1_BatchRunRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  BatchStatus(argument: _ctk_analysis_v1_BatchRunRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  BatchStatus(argument: _ctk_analysis_v1_BatchRunRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  BatchStatus(argument: _ctk_analysis_v1_BatchRunRequest, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  batchStatus(argument: _ctk_analysis_v1_BatchRunRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  batchStatus(argument: _ctk_analysis_v1_BatchRunRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  batchStatus(argument: _ctk_analysis_v1_BatchRunRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  batchStatus(argument: _ctk_analysis_v1_BatchRunRequest, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;

  CallGraph(argument: _ctk_analysis_v1_CallGraphRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_CallGraphResponse__Output>): grpc.ClientUnaryCall;
  CallGraph(argument: _ctk_analysis_v1_CallGraphRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_CallGraphResponse__Output>): grpc.ClientUnaryCall;
  CallGraph(argument: _ctk_analysis_v1_CallGraphRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_CallGraphResponse__Output>): grpc.ClientUnaryCall;
  CallGraph(argument: _ctk_analysis_v1_CallGraphRequest, callback: grpc.requestCallback<_ctk_analysis_v1_CallGraphResponse__Output>): grpc.ClientUnaryCall;
  callGraph(argument: _ctk_analysis_v1_CallGraphRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_CallGraphResponse__Output>): grpc.ClientUnaryCall;
  callGraph(argument: _ctk_analysis_v1_CallGraphRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_CallGraphResponse__Output>): grpc.ClientUnaryCall;
  callGraph(argument: _ctk_analysis_v1_CallGraphRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_CallGraphResponse__Output>): grpc.ClientUnaryCall;
  callGraph(argument: _ctk_analysis_v1_CallGraphRequest, callback: grpc.requestCallback<_ctk_analysis_v1_CallGraphResponse__Output>): grpc.ClientUnaryCall;

  CancelBatch(argument: _ctk_analysis_v1_BatchControlRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  CancelBatch(argument: _ctk_analysis_v1_BatchControlRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  CancelBatch(argument: _ctk_analysis_v1_BatchControlRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  CancelBatch(argument: _ctk_analysis_v1_BatchControlRequest, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  cancelBatch(argument: _ctk_analysis_v1_BatchControlRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  cancelBatch(argument: _ctk_analysis_v1_BatchControlRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  cancelBatch(argument: _ctk_analysis_v1_BatchControlRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  cancelBatch(argument: _ctk_analysis_v1_BatchControlRequest, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;

  Cfg(argument: _ctk_analysis_v1_CfgRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_CfgResponse__Output>): grpc.ClientUnaryCall;
  Cfg(argument: _ctk_analysis_v1_CfgRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_CfgResponse__Output>): grpc.ClientUnaryCall;
  Cfg(argument: _ctk_analysis_v1_CfgRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_CfgResponse__Output>): grpc.ClientUnaryCall;
  Cfg(argument: _ctk_analysis_v1_CfgRequest, callback: grpc.requestCallback<_ctk_analysis_v1_CfgResponse__Output>): grpc.ClientUnaryCall;
  cfg(argument: _ctk_analysis_v1_CfgRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_CfgResponse__Output>): grpc.ClientUnaryCall;
  cfg(argument: _ctk_analysis_v1_CfgRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_CfgResponse__Output>): grpc.ClientUnaryCall;
  cfg(argument: _ctk_analysis_v1_CfgRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_CfgResponse__Output>): grpc.ClientUnaryCall;
  cfg(argument: _ctk_analysis_v1_CfgRequest, callback: grpc.requestCallback<_ctk_analysis_v1_CfgResponse__Output>): grpc.ClientUnaryCall;

  ResumeBatch(argument: _ctk_analysis_v1_BatchControlRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  ResumeBatch(argument: _ctk_analysis_v1_BatchControlRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  ResumeBatch(argument: _ctk_analysis_v1_BatchControlRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  ResumeBatch(argument: _ctk_analysis_v1_BatchControlRequest, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  resumeBatch(argument: _ctk_analysis_v1_BatchControlRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  resumeBatch(argument: _ctk_analysis_v1_BatchControlRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  resumeBatch(argument: _ctk_analysis_v1_BatchControlRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  resumeBatch(argument: _ctk_analysis_v1_BatchControlRequest, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;

  RetryBatch(argument: _ctk_analysis_v1_BatchControlRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  RetryBatch(argument: _ctk_analysis_v1_BatchControlRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  RetryBatch(argument: _ctk_analysis_v1_BatchControlRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  RetryBatch(argument: _ctk_analysis_v1_BatchControlRequest, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  retryBatch(argument: _ctk_analysis_v1_BatchControlRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  retryBatch(argument: _ctk_analysis_v1_BatchControlRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  retryBatch(argument: _ctk_analysis_v1_BatchControlRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  retryBatch(argument: _ctk_analysis_v1_BatchControlRequest, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;

  RunScript(argument: _ctk_analysis_v1_ScriptRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_ScriptResponse__Output>): grpc.ClientUnaryCall;
  RunScript(argument: _ctk_analysis_v1_ScriptRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_ScriptResponse__Output>): grpc.ClientUnaryCall;
  RunScript(argument: _ctk_analysis_v1_ScriptRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_ScriptResponse__Output>): grpc.ClientUnaryCall;
  RunScript(argument: _ctk_analysis_v1_ScriptRequest, callback: grpc.requestCallback<_ctk_analysis_v1_ScriptResponse__Output>): grpc.ClientUnaryCall;
  runScript(argument: _ctk_analysis_v1_ScriptRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_ScriptResponse__Output>): grpc.ClientUnaryCall;
  runScript(argument: _ctk_analysis_v1_ScriptRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_ScriptResponse__Output>): grpc.ClientUnaryCall;
  runScript(argument: _ctk_analysis_v1_ScriptRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_ScriptResponse__Output>): grpc.ClientUnaryCall;
  runScript(argument: _ctk_analysis_v1_ScriptRequest, callback: grpc.requestCallback<_ctk_analysis_v1_ScriptResponse__Output>): grpc.ClientUnaryCall;

  StartBatch(argument: _ctk_analysis_v1_StartBatchRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  StartBatch(argument: _ctk_analysis_v1_StartBatchRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  StartBatch(argument: _ctk_analysis_v1_StartBatchRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  StartBatch(argument: _ctk_analysis_v1_StartBatchRequest, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  startBatch(argument: _ctk_analysis_v1_StartBatchRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  startBatch(argument: _ctk_analysis_v1_StartBatchRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  startBatch(argument: _ctk_analysis_v1_StartBatchRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;
  startBatch(argument: _ctk_analysis_v1_StartBatchRequest, callback: grpc.requestCallback<_ctk_analysis_v1_BatchRun__Output>): grpc.ClientUnaryCall;

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
  BatchStatus: grpc.handleUnaryCall<_ctk_analysis_v1_BatchRunRequest__Output, _ctk_analysis_v1_BatchRun>;

  CallGraph: grpc.handleUnaryCall<_ctk_analysis_v1_CallGraphRequest__Output, _ctk_analysis_v1_CallGraphResponse>;

  CancelBatch: grpc.handleUnaryCall<_ctk_analysis_v1_BatchControlRequest__Output, _ctk_analysis_v1_BatchRun>;

  Cfg: grpc.handleUnaryCall<_ctk_analysis_v1_CfgRequest__Output, _ctk_analysis_v1_CfgResponse>;

  ResumeBatch: grpc.handleUnaryCall<_ctk_analysis_v1_BatchControlRequest__Output, _ctk_analysis_v1_BatchRun>;

  RetryBatch: grpc.handleUnaryCall<_ctk_analysis_v1_BatchControlRequest__Output, _ctk_analysis_v1_BatchRun>;

  RunScript: grpc.handleUnaryCall<_ctk_analysis_v1_ScriptRequest__Output, _ctk_analysis_v1_ScriptResponse>;

  StartBatch: grpc.handleUnaryCall<_ctk_analysis_v1_StartBatchRequest__Output, _ctk_analysis_v1_BatchRun>;

  Traverse: grpc.handleUnaryCall<_ctk_analysis_v1_TraverseRequest__Output, _ctk_analysis_v1_TraverseResponse>;

}

export interface AnalysisServiceDefinition extends grpc.ServiceDefinition {
  BatchStatus: MethodDefinition<_ctk_analysis_v1_BatchRunRequest, _ctk_analysis_v1_BatchRun, _ctk_analysis_v1_BatchRunRequest__Output, _ctk_analysis_v1_BatchRun__Output>
  CallGraph: MethodDefinition<_ctk_analysis_v1_CallGraphRequest, _ctk_analysis_v1_CallGraphResponse, _ctk_analysis_v1_CallGraphRequest__Output, _ctk_analysis_v1_CallGraphResponse__Output>
  CancelBatch: MethodDefinition<_ctk_analysis_v1_BatchControlRequest, _ctk_analysis_v1_BatchRun, _ctk_analysis_v1_BatchControlRequest__Output, _ctk_analysis_v1_BatchRun__Output>
  Cfg: MethodDefinition<_ctk_analysis_v1_CfgRequest, _ctk_analysis_v1_CfgResponse, _ctk_analysis_v1_CfgRequest__Output, _ctk_analysis_v1_CfgResponse__Output>
  ResumeBatch: MethodDefinition<_ctk_analysis_v1_BatchControlRequest, _ctk_analysis_v1_BatchRun, _ctk_analysis_v1_BatchControlRequest__Output, _ctk_analysis_v1_BatchRun__Output>
  RetryBatch: MethodDefinition<_ctk_analysis_v1_BatchControlRequest, _ctk_analysis_v1_BatchRun, _ctk_analysis_v1_BatchControlRequest__Output, _ctk_analysis_v1_BatchRun__Output>
  RunScript: MethodDefinition<_ctk_analysis_v1_ScriptRequest, _ctk_analysis_v1_ScriptResponse, _ctk_analysis_v1_ScriptRequest__Output, _ctk_analysis_v1_ScriptResponse__Output>
  StartBatch: MethodDefinition<_ctk_analysis_v1_StartBatchRequest, _ctk_analysis_v1_BatchRun, _ctk_analysis_v1_StartBatchRequest__Output, _ctk_analysis_v1_BatchRun__Output>
  Traverse: MethodDefinition<_ctk_analysis_v1_TraverseRequest, _ctk_analysis_v1_TraverseResponse, _ctk_analysis_v1_TraverseRequest__Output, _ctk_analysis_v1_TraverseResponse__Output>
}
