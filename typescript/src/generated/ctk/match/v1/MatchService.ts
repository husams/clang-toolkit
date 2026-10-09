// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_service.proto

import type * as grpc from '@grpc/grpc-js'
import type { MethodDefinition } from '@grpc/proto-loader'
import type { AttachSessionRequest as _ctk_match_v1_AttachSessionRequest, AttachSessionRequest__Output as _ctk_match_v1_AttachSessionRequest__Output } from '../../../ctk/match/v1/AttachSessionRequest.js';
import type { CloseSessionRequest as _ctk_match_v1_CloseSessionRequest, CloseSessionRequest__Output as _ctk_match_v1_CloseSessionRequest__Output } from '../../../ctk/match/v1/CloseSessionRequest.js';
import type { CloseSessionResponse as _ctk_match_v1_CloseSessionResponse, CloseSessionResponse__Output as _ctk_match_v1_CloseSessionResponse__Output } from '../../../ctk/match/v1/CloseSessionResponse.js';
import type { ListSessionsRequest as _ctk_match_v1_ListSessionsRequest, ListSessionsRequest__Output as _ctk_match_v1_ListSessionsRequest__Output } from '../../../ctk/match/v1/ListSessionsRequest.js';
import type { ListSessionsResponse as _ctk_match_v1_ListSessionsResponse, ListSessionsResponse__Output as _ctk_match_v1_ListSessionsResponse__Output } from '../../../ctk/match/v1/ListSessionsResponse.js';
import type { MatchRequest as _ctk_match_v1_MatchRequest, MatchRequest__Output as _ctk_match_v1_MatchRequest__Output } from '../../../ctk/match/v1/MatchRequest.js';
import type { MatchResponse as _ctk_match_v1_MatchResponse, MatchResponse__Output as _ctk_match_v1_MatchResponse__Output } from '../../../ctk/match/v1/MatchResponse.js';
import type { MatchStreamEvent as _ctk_match_v1_MatchStreamEvent, MatchStreamEvent__Output as _ctk_match_v1_MatchStreamEvent__Output } from '../../../ctk/match/v1/MatchStreamEvent.js';
import type { ParseRequest as _ctk_match_v1_ParseRequest, ParseRequest__Output as _ctk_match_v1_ParseRequest__Output } from '../../../ctk/match/v1/ParseRequest.js';
import type { ParseResponse as _ctk_match_v1_ParseResponse, ParseResponse__Output as _ctk_match_v1_ParseResponse__Output } from '../../../ctk/match/v1/ParseResponse.js';
import type { PruneCachesRequest as _ctk_match_v1_PruneCachesRequest, PruneCachesRequest__Output as _ctk_match_v1_PruneCachesRequest__Output } from '../../../ctk/match/v1/PruneCachesRequest.js';
import type { PruneCachesResponse as _ctk_match_v1_PruneCachesResponse, PruneCachesResponse__Output as _ctk_match_v1_PruneCachesResponse__Output } from '../../../ctk/match/v1/PruneCachesResponse.js';
import type { ServerStatusRequest as _ctk_match_v1_ServerStatusRequest, ServerStatusRequest__Output as _ctk_match_v1_ServerStatusRequest__Output } from '../../../ctk/match/v1/ServerStatusRequest.js';
import type { ServerStatusResponse as _ctk_match_v1_ServerStatusResponse, ServerStatusResponse__Output as _ctk_match_v1_ServerStatusResponse__Output } from '../../../ctk/match/v1/ServerStatusResponse.js';
import type { SessionInfo as _ctk_match_v1_SessionInfo, SessionInfo__Output as _ctk_match_v1_SessionInfo__Output } from '../../../ctk/match/v1/SessionInfo.js';

export interface MatchServiceClient extends grpc.Client {
  AttachSession(argument: _ctk_match_v1_AttachSessionRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_SessionInfo__Output>): grpc.ClientUnaryCall;
  AttachSession(argument: _ctk_match_v1_AttachSessionRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_SessionInfo__Output>): grpc.ClientUnaryCall;
  AttachSession(argument: _ctk_match_v1_AttachSessionRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_SessionInfo__Output>): grpc.ClientUnaryCall;
  AttachSession(argument: _ctk_match_v1_AttachSessionRequest, callback: grpc.requestCallback<_ctk_match_v1_SessionInfo__Output>): grpc.ClientUnaryCall;
  attachSession(argument: _ctk_match_v1_AttachSessionRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_SessionInfo__Output>): grpc.ClientUnaryCall;
  attachSession(argument: _ctk_match_v1_AttachSessionRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_SessionInfo__Output>): grpc.ClientUnaryCall;
  attachSession(argument: _ctk_match_v1_AttachSessionRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_SessionInfo__Output>): grpc.ClientUnaryCall;
  attachSession(argument: _ctk_match_v1_AttachSessionRequest, callback: grpc.requestCallback<_ctk_match_v1_SessionInfo__Output>): grpc.ClientUnaryCall;

  CloseSession(argument: _ctk_match_v1_CloseSessionRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;
  CloseSession(argument: _ctk_match_v1_CloseSessionRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;
  CloseSession(argument: _ctk_match_v1_CloseSessionRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;
  CloseSession(argument: _ctk_match_v1_CloseSessionRequest, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;
  closeSession(argument: _ctk_match_v1_CloseSessionRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;
  closeSession(argument: _ctk_match_v1_CloseSessionRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;
  closeSession(argument: _ctk_match_v1_CloseSessionRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;
  closeSession(argument: _ctk_match_v1_CloseSessionRequest, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;

  ListSessions(argument: _ctk_match_v1_ListSessionsRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ListSessionsResponse__Output>): grpc.ClientUnaryCall;
  ListSessions(argument: _ctk_match_v1_ListSessionsRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_ListSessionsResponse__Output>): grpc.ClientUnaryCall;
  ListSessions(argument: _ctk_match_v1_ListSessionsRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ListSessionsResponse__Output>): grpc.ClientUnaryCall;
  ListSessions(argument: _ctk_match_v1_ListSessionsRequest, callback: grpc.requestCallback<_ctk_match_v1_ListSessionsResponse__Output>): grpc.ClientUnaryCall;
  listSessions(argument: _ctk_match_v1_ListSessionsRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ListSessionsResponse__Output>): grpc.ClientUnaryCall;
  listSessions(argument: _ctk_match_v1_ListSessionsRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_ListSessionsResponse__Output>): grpc.ClientUnaryCall;
  listSessions(argument: _ctk_match_v1_ListSessionsRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ListSessionsResponse__Output>): grpc.ClientUnaryCall;
  listSessions(argument: _ctk_match_v1_ListSessionsRequest, callback: grpc.requestCallback<_ctk_match_v1_ListSessionsResponse__Output>): grpc.ClientUnaryCall;

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

  PruneCaches(argument: _ctk_match_v1_PruneCachesRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_PruneCachesResponse__Output>): grpc.ClientUnaryCall;
  PruneCaches(argument: _ctk_match_v1_PruneCachesRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_PruneCachesResponse__Output>): grpc.ClientUnaryCall;
  PruneCaches(argument: _ctk_match_v1_PruneCachesRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_PruneCachesResponse__Output>): grpc.ClientUnaryCall;
  PruneCaches(argument: _ctk_match_v1_PruneCachesRequest, callback: grpc.requestCallback<_ctk_match_v1_PruneCachesResponse__Output>): grpc.ClientUnaryCall;
  pruneCaches(argument: _ctk_match_v1_PruneCachesRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_PruneCachesResponse__Output>): grpc.ClientUnaryCall;
  pruneCaches(argument: _ctk_match_v1_PruneCachesRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_PruneCachesResponse__Output>): grpc.ClientUnaryCall;
  pruneCaches(argument: _ctk_match_v1_PruneCachesRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_PruneCachesResponse__Output>): grpc.ClientUnaryCall;
  pruneCaches(argument: _ctk_match_v1_PruneCachesRequest, callback: grpc.requestCallback<_ctk_match_v1_PruneCachesResponse__Output>): grpc.ClientUnaryCall;

  ServerStatus(argument: _ctk_match_v1_ServerStatusRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ServerStatusResponse__Output>): grpc.ClientUnaryCall;
  ServerStatus(argument: _ctk_match_v1_ServerStatusRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_ServerStatusResponse__Output>): grpc.ClientUnaryCall;
  ServerStatus(argument: _ctk_match_v1_ServerStatusRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ServerStatusResponse__Output>): grpc.ClientUnaryCall;
  ServerStatus(argument: _ctk_match_v1_ServerStatusRequest, callback: grpc.requestCallback<_ctk_match_v1_ServerStatusResponse__Output>): grpc.ClientUnaryCall;
  serverStatus(argument: _ctk_match_v1_ServerStatusRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ServerStatusResponse__Output>): grpc.ClientUnaryCall;
  serverStatus(argument: _ctk_match_v1_ServerStatusRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_ServerStatusResponse__Output>): grpc.ClientUnaryCall;
  serverStatus(argument: _ctk_match_v1_ServerStatusRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ServerStatusResponse__Output>): grpc.ClientUnaryCall;
  serverStatus(argument: _ctk_match_v1_ServerStatusRequest, callback: grpc.requestCallback<_ctk_match_v1_ServerStatusResponse__Output>): grpc.ClientUnaryCall;

  StreamMatch(argument: _ctk_match_v1_MatchRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_ctk_match_v1_MatchStreamEvent__Output>;
  StreamMatch(argument: _ctk_match_v1_MatchRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_ctk_match_v1_MatchStreamEvent__Output>;
  streamMatch(argument: _ctk_match_v1_MatchRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_ctk_match_v1_MatchStreamEvent__Output>;
  streamMatch(argument: _ctk_match_v1_MatchRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_ctk_match_v1_MatchStreamEvent__Output>;

}

export interface MatchServiceHandlers extends grpc.UntypedServiceImplementation {
  AttachSession: grpc.handleUnaryCall<_ctk_match_v1_AttachSessionRequest__Output, _ctk_match_v1_SessionInfo>;

  CloseSession: grpc.handleUnaryCall<_ctk_match_v1_CloseSessionRequest__Output, _ctk_match_v1_CloseSessionResponse>;

  ListSessions: grpc.handleUnaryCall<_ctk_match_v1_ListSessionsRequest__Output, _ctk_match_v1_ListSessionsResponse>;

  Match: grpc.handleUnaryCall<_ctk_match_v1_MatchRequest__Output, _ctk_match_v1_MatchResponse>;

  Parse: grpc.handleUnaryCall<_ctk_match_v1_ParseRequest__Output, _ctk_match_v1_ParseResponse>;

  PruneCaches: grpc.handleUnaryCall<_ctk_match_v1_PruneCachesRequest__Output, _ctk_match_v1_PruneCachesResponse>;

  ServerStatus: grpc.handleUnaryCall<_ctk_match_v1_ServerStatusRequest__Output, _ctk_match_v1_ServerStatusResponse>;

  StreamMatch: grpc.handleServerStreamingCall<_ctk_match_v1_MatchRequest__Output, _ctk_match_v1_MatchStreamEvent>;

}

export interface MatchServiceDefinition extends grpc.ServiceDefinition {
  AttachSession: MethodDefinition<_ctk_match_v1_AttachSessionRequest, _ctk_match_v1_SessionInfo, _ctk_match_v1_AttachSessionRequest__Output, _ctk_match_v1_SessionInfo__Output>
  CloseSession: MethodDefinition<_ctk_match_v1_CloseSessionRequest, _ctk_match_v1_CloseSessionResponse, _ctk_match_v1_CloseSessionRequest__Output, _ctk_match_v1_CloseSessionResponse__Output>
  ListSessions: MethodDefinition<_ctk_match_v1_ListSessionsRequest, _ctk_match_v1_ListSessionsResponse, _ctk_match_v1_ListSessionsRequest__Output, _ctk_match_v1_ListSessionsResponse__Output>
  Match: MethodDefinition<_ctk_match_v1_MatchRequest, _ctk_match_v1_MatchResponse, _ctk_match_v1_MatchRequest__Output, _ctk_match_v1_MatchResponse__Output>
  Parse: MethodDefinition<_ctk_match_v1_ParseRequest, _ctk_match_v1_ParseResponse, _ctk_match_v1_ParseRequest__Output, _ctk_match_v1_ParseResponse__Output>
  PruneCaches: MethodDefinition<_ctk_match_v1_PruneCachesRequest, _ctk_match_v1_PruneCachesResponse, _ctk_match_v1_PruneCachesRequest__Output, _ctk_match_v1_PruneCachesResponse__Output>
  ServerStatus: MethodDefinition<_ctk_match_v1_ServerStatusRequest, _ctk_match_v1_ServerStatusResponse, _ctk_match_v1_ServerStatusRequest__Output, _ctk_match_v1_ServerStatusResponse__Output>
  StreamMatch: MethodDefinition<_ctk_match_v1_MatchRequest, _ctk_match_v1_MatchStreamEvent, _ctk_match_v1_MatchRequest__Output, _ctk_match_v1_MatchStreamEvent__Output>
}
