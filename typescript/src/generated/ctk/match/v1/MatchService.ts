// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_service.proto

import type * as grpc from '@grpc/grpc-js'
import type { MethodDefinition } from '@grpc/proto-loader'
import type { CloseSessionRequest as _ctk_match_v1_CloseSessionRequest, CloseSessionRequest__Output as _ctk_match_v1_CloseSessionRequest__Output } from '../../../ctk/match/v1/CloseSessionRequest.js';
import type { CloseSessionResponse as _ctk_match_v1_CloseSessionResponse, CloseSessionResponse__Output as _ctk_match_v1_CloseSessionResponse__Output } from '../../../ctk/match/v1/CloseSessionResponse.js';
import type { MatchRequest as _ctk_match_v1_MatchRequest, MatchRequest__Output as _ctk_match_v1_MatchRequest__Output } from '../../../ctk/match/v1/MatchRequest.js';
import type { MatchResponse as _ctk_match_v1_MatchResponse, MatchResponse__Output as _ctk_match_v1_MatchResponse__Output } from '../../../ctk/match/v1/MatchResponse.js';
import type { MatchStreamEvent as _ctk_match_v1_MatchStreamEvent, MatchStreamEvent__Output as _ctk_match_v1_MatchStreamEvent__Output } from '../../../ctk/match/v1/MatchStreamEvent.js';
import type { ParseRequest as _ctk_match_v1_ParseRequest, ParseRequest__Output as _ctk_match_v1_ParseRequest__Output } from '../../../ctk/match/v1/ParseRequest.js';
import type { ParseResponse as _ctk_match_v1_ParseResponse, ParseResponse__Output as _ctk_match_v1_ParseResponse__Output } from '../../../ctk/match/v1/ParseResponse.js';

export interface MatchServiceClient extends grpc.Client {
  CloseSession(argument: _ctk_match_v1_CloseSessionRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;
  CloseSession(argument: _ctk_match_v1_CloseSessionRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;
  CloseSession(argument: _ctk_match_v1_CloseSessionRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;
  CloseSession(argument: _ctk_match_v1_CloseSessionRequest, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;
  closeSession(argument: _ctk_match_v1_CloseSessionRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;
  closeSession(argument: _ctk_match_v1_CloseSessionRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;
  closeSession(argument: _ctk_match_v1_CloseSessionRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;
  closeSession(argument: _ctk_match_v1_CloseSessionRequest, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;

  Match(argument: _ctk_match_v1_MatchRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_MatchResponse__Output>): grpc.ClientUnaryCall;
  Match(argument: _ctk_match_v1_MatchRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_MatchResponse__Output>): grpc.ClientUnaryCall;
  Match(argument: _ctk_match_v1_MatchRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_MatchResponse__Output>): grpc.ClientUnaryCall;
  Match(argument: _ctk_match_v1_MatchRequest, callback: grpc.requestCallback<_ctk_match_v1_MatchResponse__Output>): grpc.ClientUnaryCall;
  match(argument: _ctk_match_v1_MatchRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_MatchResponse__Output>): grpc.ClientUnaryCall;
  match(argument: _ctk_match_v1_MatchRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_MatchResponse__Output>): grpc.ClientUnaryCall;
  match(argument: _ctk_match_v1_MatchRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_MatchResponse__Output>): grpc.ClientUnaryCall;
  match(argument: _ctk_match_v1_MatchRequest, callback: grpc.requestCallback<_ctk_match_v1_MatchResponse__Output>): grpc.ClientUnaryCall;

  Parse(argument: _ctk_match_v1_ParseRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ParseResponse__Output>): grpc.ClientUnaryCall;
  Parse(argument: _ctk_match_v1_ParseRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_ParseResponse__Output>): grpc.ClientUnaryCall;
  Parse(argument: _ctk_match_v1_ParseRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ParseResponse__Output>): grpc.ClientUnaryCall;
  Parse(argument: _ctk_match_v1_ParseRequest, callback: grpc.requestCallback<_ctk_match_v1_ParseResponse__Output>): grpc.ClientUnaryCall;
  parse(argument: _ctk_match_v1_ParseRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ParseResponse__Output>): grpc.ClientUnaryCall;
  parse(argument: _ctk_match_v1_ParseRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_ParseResponse__Output>): grpc.ClientUnaryCall;
  parse(argument: _ctk_match_v1_ParseRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ParseResponse__Output>): grpc.ClientUnaryCall;
  parse(argument: _ctk_match_v1_ParseRequest, callback: grpc.requestCallback<_ctk_match_v1_ParseResponse__Output>): grpc.ClientUnaryCall;

  StreamMatch(argument: _ctk_match_v1_MatchRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_ctk_match_v1_MatchStreamEvent__Output>;
  StreamMatch(argument: _ctk_match_v1_MatchRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_ctk_match_v1_MatchStreamEvent__Output>;
  streamMatch(argument: _ctk_match_v1_MatchRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_ctk_match_v1_MatchStreamEvent__Output>;
  streamMatch(argument: _ctk_match_v1_MatchRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_ctk_match_v1_MatchStreamEvent__Output>;

}

export interface MatchServiceHandlers extends grpc.UntypedServiceImplementation {
  CloseSession: grpc.handleUnaryCall<_ctk_match_v1_CloseSessionRequest__Output, _ctk_match_v1_CloseSessionResponse>;

  Match: grpc.handleUnaryCall<_ctk_match_v1_MatchRequest__Output, _ctk_match_v1_MatchResponse>;

  Parse: grpc.handleUnaryCall<_ctk_match_v1_ParseRequest__Output, _ctk_match_v1_ParseResponse>;

  StreamMatch: grpc.handleServerStreamingCall<_ctk_match_v1_MatchRequest__Output, _ctk_match_v1_MatchStreamEvent>;

}

export interface MatchServiceDefinition extends grpc.ServiceDefinition {
  CloseSession: MethodDefinition<_ctk_match_v1_CloseSessionRequest, _ctk_match_v1_CloseSessionResponse, _ctk_match_v1_CloseSessionRequest__Output, _ctk_match_v1_CloseSessionResponse__Output>
  Match: MethodDefinition<_ctk_match_v1_MatchRequest, _ctk_match_v1_MatchResponse, _ctk_match_v1_MatchRequest__Output, _ctk_match_v1_MatchResponse__Output>
  Parse: MethodDefinition<_ctk_match_v1_ParseRequest, _ctk_match_v1_ParseResponse, _ctk_match_v1_ParseRequest__Output, _ctk_match_v1_ParseResponse__Output>
  StreamMatch: MethodDefinition<_ctk_match_v1_MatchRequest, _ctk_match_v1_MatchStreamEvent, _ctk_match_v1_MatchRequest__Output, _ctk_match_v1_MatchStreamEvent__Output>
}
