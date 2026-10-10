// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_service.proto

import type * as grpc from '@grpc/grpc-js'
import type { MethodDefinition } from '@grpc/proto-loader'
import type { AttachSessionRequest as _ctk_match_v1_AttachSessionRequest, AttachSessionRequest__Output as _ctk_match_v1_AttachSessionRequest__Output } from '../../../ctk/match/v1/AttachSessionRequest.js';
import type { CloseAllFilesRequest as _ctk_match_v1_CloseAllFilesRequest, CloseAllFilesRequest__Output as _ctk_match_v1_CloseAllFilesRequest__Output } from '../../../ctk/match/v1/CloseAllFilesRequest.js';
import type { CloseFileRequest as _ctk_match_v1_CloseFileRequest, CloseFileRequest__Output as _ctk_match_v1_CloseFileRequest__Output } from '../../../ctk/match/v1/CloseFileRequest.js';
import type { CloseFileResponse as _ctk_match_v1_CloseFileResponse, CloseFileResponse__Output as _ctk_match_v1_CloseFileResponse__Output } from '../../../ctk/match/v1/CloseFileResponse.js';
import type { CloseSessionRequest as _ctk_match_v1_CloseSessionRequest, CloseSessionRequest__Output as _ctk_match_v1_CloseSessionRequest__Output } from '../../../ctk/match/v1/CloseSessionRequest.js';
import type { CloseSessionResponse as _ctk_match_v1_CloseSessionResponse, CloseSessionResponse__Output as _ctk_match_v1_CloseSessionResponse__Output } from '../../../ctk/match/v1/CloseSessionResponse.js';
import type { DescribeFileRequest as _ctk_match_v1_DescribeFileRequest, DescribeFileRequest__Output as _ctk_match_v1_DescribeFileRequest__Output } from '../../../ctk/match/v1/DescribeFileRequest.js';
import type { DiscoverFilesRequest as _ctk_match_v1_DiscoverFilesRequest, DiscoverFilesRequest__Output as _ctk_match_v1_DiscoverFilesRequest__Output } from '../../../ctk/match/v1/DiscoverFilesRequest.js';
import type { DiscoverFilesResponse as _ctk_match_v1_DiscoverFilesResponse, DiscoverFilesResponse__Output as _ctk_match_v1_DiscoverFilesResponse__Output } from '../../../ctk/match/v1/DiscoverFilesResponse.js';
import type { FileInfo as _ctk_match_v1_FileInfo, FileInfo__Output as _ctk_match_v1_FileInfo__Output } from '../../../ctk/match/v1/FileInfo.js';
import type { ListFilesRequest as _ctk_match_v1_ListFilesRequest, ListFilesRequest__Output as _ctk_match_v1_ListFilesRequest__Output } from '../../../ctk/match/v1/ListFilesRequest.js';
import type { ListFilesResponse as _ctk_match_v1_ListFilesResponse, ListFilesResponse__Output as _ctk_match_v1_ListFilesResponse__Output } from '../../../ctk/match/v1/ListFilesResponse.js';
import type { ListSessionsRequest as _ctk_match_v1_ListSessionsRequest, ListSessionsRequest__Output as _ctk_match_v1_ListSessionsRequest__Output } from '../../../ctk/match/v1/ListSessionsRequest.js';
import type { ListSessionsResponse as _ctk_match_v1_ListSessionsResponse, ListSessionsResponse__Output as _ctk_match_v1_ListSessionsResponse__Output } from '../../../ctk/match/v1/ListSessionsResponse.js';
import type { MatchRequest as _ctk_match_v1_MatchRequest, MatchRequest__Output as _ctk_match_v1_MatchRequest__Output } from '../../../ctk/match/v1/MatchRequest.js';
import type { MatchResponse as _ctk_match_v1_MatchResponse, MatchResponse__Output as _ctk_match_v1_MatchResponse__Output } from '../../../ctk/match/v1/MatchResponse.js';
import type { MatchStreamEvent as _ctk_match_v1_MatchStreamEvent, MatchStreamEvent__Output as _ctk_match_v1_MatchStreamEvent__Output } from '../../../ctk/match/v1/MatchStreamEvent.js';
import type { OpenFileRequest as _ctk_match_v1_OpenFileRequest, OpenFileRequest__Output as _ctk_match_v1_OpenFileRequest__Output } from '../../../ctk/match/v1/OpenFileRequest.js';
import type { OpenResourceScopeRequest as _ctk_match_v1_OpenResourceScopeRequest, OpenResourceScopeRequest__Output as _ctk_match_v1_OpenResourceScopeRequest__Output } from '../../../ctk/match/v1/OpenResourceScopeRequest.js';
import type { ParseRequest as _ctk_match_v1_ParseRequest, ParseRequest__Output as _ctk_match_v1_ParseRequest__Output } from '../../../ctk/match/v1/ParseRequest.js';
import type { ParseResponse as _ctk_match_v1_ParseResponse, ParseResponse__Output as _ctk_match_v1_ParseResponse__Output } from '../../../ctk/match/v1/ParseResponse.js';
import type { PruneCachesRequest as _ctk_match_v1_PruneCachesRequest, PruneCachesRequest__Output as _ctk_match_v1_PruneCachesRequest__Output } from '../../../ctk/match/v1/PruneCachesRequest.js';
import type { PruneCachesResponse as _ctk_match_v1_PruneCachesResponse, PruneCachesResponse__Output as _ctk_match_v1_PruneCachesResponse__Output } from '../../../ctk/match/v1/PruneCachesResponse.js';
import type { RefreshFileRequest as _ctk_match_v1_RefreshFileRequest, RefreshFileRequest__Output as _ctk_match_v1_RefreshFileRequest__Output } from '../../../ctk/match/v1/RefreshFileRequest.js';
import type { ResourceScopeInfo as _ctk_match_v1_ResourceScopeInfo, ResourceScopeInfo__Output as _ctk_match_v1_ResourceScopeInfo__Output } from '../../../ctk/match/v1/ResourceScopeInfo.js';
import type { ResourceScopeRequest as _ctk_match_v1_ResourceScopeRequest, ResourceScopeRequest__Output as _ctk_match_v1_ResourceScopeRequest__Output } from '../../../ctk/match/v1/ResourceScopeRequest.js';
import type { ResourceStatusRequest as _ctk_match_v1_ResourceStatusRequest, ResourceStatusRequest__Output as _ctk_match_v1_ResourceStatusRequest__Output } from '../../../ctk/match/v1/ResourceStatusRequest.js';
import type { ResourceStatusResponse as _ctk_match_v1_ResourceStatusResponse, ResourceStatusResponse__Output as _ctk_match_v1_ResourceStatusResponse__Output } from '../../../ctk/match/v1/ResourceStatusResponse.js';
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

  CancelResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  CancelResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  CancelResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  CancelResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  cancelResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  cancelResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  cancelResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  cancelResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;

  CloseAllFiles(argument: _ctk_match_v1_CloseAllFilesRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_CloseFileResponse__Output>): grpc.ClientUnaryCall;
  CloseAllFiles(argument: _ctk_match_v1_CloseAllFilesRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_CloseFileResponse__Output>): grpc.ClientUnaryCall;
  CloseAllFiles(argument: _ctk_match_v1_CloseAllFilesRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_CloseFileResponse__Output>): grpc.ClientUnaryCall;
  CloseAllFiles(argument: _ctk_match_v1_CloseAllFilesRequest, callback: grpc.requestCallback<_ctk_match_v1_CloseFileResponse__Output>): grpc.ClientUnaryCall;
  closeAllFiles(argument: _ctk_match_v1_CloseAllFilesRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_CloseFileResponse__Output>): grpc.ClientUnaryCall;
  closeAllFiles(argument: _ctk_match_v1_CloseAllFilesRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_CloseFileResponse__Output>): grpc.ClientUnaryCall;
  closeAllFiles(argument: _ctk_match_v1_CloseAllFilesRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_CloseFileResponse__Output>): grpc.ClientUnaryCall;
  closeAllFiles(argument: _ctk_match_v1_CloseAllFilesRequest, callback: grpc.requestCallback<_ctk_match_v1_CloseFileResponse__Output>): grpc.ClientUnaryCall;

  CloseFile(argument: _ctk_match_v1_CloseFileRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_CloseFileResponse__Output>): grpc.ClientUnaryCall;
  CloseFile(argument: _ctk_match_v1_CloseFileRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_CloseFileResponse__Output>): grpc.ClientUnaryCall;
  CloseFile(argument: _ctk_match_v1_CloseFileRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_CloseFileResponse__Output>): grpc.ClientUnaryCall;
  CloseFile(argument: _ctk_match_v1_CloseFileRequest, callback: grpc.requestCallback<_ctk_match_v1_CloseFileResponse__Output>): grpc.ClientUnaryCall;
  closeFile(argument: _ctk_match_v1_CloseFileRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_CloseFileResponse__Output>): grpc.ClientUnaryCall;
  closeFile(argument: _ctk_match_v1_CloseFileRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_CloseFileResponse__Output>): grpc.ClientUnaryCall;
  closeFile(argument: _ctk_match_v1_CloseFileRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_CloseFileResponse__Output>): grpc.ClientUnaryCall;
  closeFile(argument: _ctk_match_v1_CloseFileRequest, callback: grpc.requestCallback<_ctk_match_v1_CloseFileResponse__Output>): grpc.ClientUnaryCall;

  CloseSession(argument: _ctk_match_v1_CloseSessionRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;
  CloseSession(argument: _ctk_match_v1_CloseSessionRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;
  CloseSession(argument: _ctk_match_v1_CloseSessionRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;
  CloseSession(argument: _ctk_match_v1_CloseSessionRequest, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;
  closeSession(argument: _ctk_match_v1_CloseSessionRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;
  closeSession(argument: _ctk_match_v1_CloseSessionRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;
  closeSession(argument: _ctk_match_v1_CloseSessionRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;
  closeSession(argument: _ctk_match_v1_CloseSessionRequest, callback: grpc.requestCallback<_ctk_match_v1_CloseSessionResponse__Output>): grpc.ClientUnaryCall;

  DescribeFile(argument: _ctk_match_v1_DescribeFileRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;
  DescribeFile(argument: _ctk_match_v1_DescribeFileRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;
  DescribeFile(argument: _ctk_match_v1_DescribeFileRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;
  DescribeFile(argument: _ctk_match_v1_DescribeFileRequest, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;
  describeFile(argument: _ctk_match_v1_DescribeFileRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;
  describeFile(argument: _ctk_match_v1_DescribeFileRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;
  describeFile(argument: _ctk_match_v1_DescribeFileRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;
  describeFile(argument: _ctk_match_v1_DescribeFileRequest, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;

  DescribeResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  DescribeResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  DescribeResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  DescribeResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  describeResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  describeResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  describeResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  describeResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;

  DiscoverFiles(argument: _ctk_match_v1_DiscoverFilesRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_DiscoverFilesResponse__Output>): grpc.ClientUnaryCall;
  DiscoverFiles(argument: _ctk_match_v1_DiscoverFilesRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_DiscoverFilesResponse__Output>): grpc.ClientUnaryCall;
  DiscoverFiles(argument: _ctk_match_v1_DiscoverFilesRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_DiscoverFilesResponse__Output>): grpc.ClientUnaryCall;
  DiscoverFiles(argument: _ctk_match_v1_DiscoverFilesRequest, callback: grpc.requestCallback<_ctk_match_v1_DiscoverFilesResponse__Output>): grpc.ClientUnaryCall;
  discoverFiles(argument: _ctk_match_v1_DiscoverFilesRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_DiscoverFilesResponse__Output>): grpc.ClientUnaryCall;
  discoverFiles(argument: _ctk_match_v1_DiscoverFilesRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_DiscoverFilesResponse__Output>): grpc.ClientUnaryCall;
  discoverFiles(argument: _ctk_match_v1_DiscoverFilesRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_DiscoverFilesResponse__Output>): grpc.ClientUnaryCall;
  discoverFiles(argument: _ctk_match_v1_DiscoverFilesRequest, callback: grpc.requestCallback<_ctk_match_v1_DiscoverFilesResponse__Output>): grpc.ClientUnaryCall;

  ListFiles(argument: _ctk_match_v1_ListFilesRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ListFilesResponse__Output>): grpc.ClientUnaryCall;
  ListFiles(argument: _ctk_match_v1_ListFilesRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_ListFilesResponse__Output>): grpc.ClientUnaryCall;
  ListFiles(argument: _ctk_match_v1_ListFilesRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ListFilesResponse__Output>): grpc.ClientUnaryCall;
  ListFiles(argument: _ctk_match_v1_ListFilesRequest, callback: grpc.requestCallback<_ctk_match_v1_ListFilesResponse__Output>): grpc.ClientUnaryCall;
  listFiles(argument: _ctk_match_v1_ListFilesRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ListFilesResponse__Output>): grpc.ClientUnaryCall;
  listFiles(argument: _ctk_match_v1_ListFilesRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_ListFilesResponse__Output>): grpc.ClientUnaryCall;
  listFiles(argument: _ctk_match_v1_ListFilesRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ListFilesResponse__Output>): grpc.ClientUnaryCall;
  listFiles(argument: _ctk_match_v1_ListFilesRequest, callback: grpc.requestCallback<_ctk_match_v1_ListFilesResponse__Output>): grpc.ClientUnaryCall;

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

  OpenFile(argument: _ctk_match_v1_OpenFileRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;
  OpenFile(argument: _ctk_match_v1_OpenFileRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;
  OpenFile(argument: _ctk_match_v1_OpenFileRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;
  OpenFile(argument: _ctk_match_v1_OpenFileRequest, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;
  openFile(argument: _ctk_match_v1_OpenFileRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;
  openFile(argument: _ctk_match_v1_OpenFileRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;
  openFile(argument: _ctk_match_v1_OpenFileRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;
  openFile(argument: _ctk_match_v1_OpenFileRequest, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;

  OpenResourceScope(argument: _ctk_match_v1_OpenResourceScopeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  OpenResourceScope(argument: _ctk_match_v1_OpenResourceScopeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  OpenResourceScope(argument: _ctk_match_v1_OpenResourceScopeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  OpenResourceScope(argument: _ctk_match_v1_OpenResourceScopeRequest, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  openResourceScope(argument: _ctk_match_v1_OpenResourceScopeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  openResourceScope(argument: _ctk_match_v1_OpenResourceScopeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  openResourceScope(argument: _ctk_match_v1_OpenResourceScopeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  openResourceScope(argument: _ctk_match_v1_OpenResourceScopeRequest, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;

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

  RefreshFile(argument: _ctk_match_v1_RefreshFileRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;
  RefreshFile(argument: _ctk_match_v1_RefreshFileRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;
  RefreshFile(argument: _ctk_match_v1_RefreshFileRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;
  RefreshFile(argument: _ctk_match_v1_RefreshFileRequest, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;
  refreshFile(argument: _ctk_match_v1_RefreshFileRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;
  refreshFile(argument: _ctk_match_v1_RefreshFileRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;
  refreshFile(argument: _ctk_match_v1_RefreshFileRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;
  refreshFile(argument: _ctk_match_v1_RefreshFileRequest, callback: grpc.requestCallback<_ctk_match_v1_FileInfo__Output>): grpc.ClientUnaryCall;

  ReleaseResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  ReleaseResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  ReleaseResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  ReleaseResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  releaseResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  releaseResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  releaseResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;
  releaseResourceScope(argument: _ctk_match_v1_ResourceScopeRequest, callback: grpc.requestCallback<_ctk_match_v1_ResourceScopeInfo__Output>): grpc.ClientUnaryCall;

  ResourceStatus(argument: _ctk_match_v1_ResourceStatusRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ResourceStatusResponse__Output>): grpc.ClientUnaryCall;
  ResourceStatus(argument: _ctk_match_v1_ResourceStatusRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_ResourceStatusResponse__Output>): grpc.ClientUnaryCall;
  ResourceStatus(argument: _ctk_match_v1_ResourceStatusRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ResourceStatusResponse__Output>): grpc.ClientUnaryCall;
  ResourceStatus(argument: _ctk_match_v1_ResourceStatusRequest, callback: grpc.requestCallback<_ctk_match_v1_ResourceStatusResponse__Output>): grpc.ClientUnaryCall;
  resourceStatus(argument: _ctk_match_v1_ResourceStatusRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ResourceStatusResponse__Output>): grpc.ClientUnaryCall;
  resourceStatus(argument: _ctk_match_v1_ResourceStatusRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_ctk_match_v1_ResourceStatusResponse__Output>): grpc.ClientUnaryCall;
  resourceStatus(argument: _ctk_match_v1_ResourceStatusRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_ctk_match_v1_ResourceStatusResponse__Output>): grpc.ClientUnaryCall;
  resourceStatus(argument: _ctk_match_v1_ResourceStatusRequest, callback: grpc.requestCallback<_ctk_match_v1_ResourceStatusResponse__Output>): grpc.ClientUnaryCall;

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

  CancelResourceScope: grpc.handleUnaryCall<_ctk_match_v1_ResourceScopeRequest__Output, _ctk_match_v1_ResourceScopeInfo>;

  CloseAllFiles: grpc.handleUnaryCall<_ctk_match_v1_CloseAllFilesRequest__Output, _ctk_match_v1_CloseFileResponse>;

  CloseFile: grpc.handleUnaryCall<_ctk_match_v1_CloseFileRequest__Output, _ctk_match_v1_CloseFileResponse>;

  CloseSession: grpc.handleUnaryCall<_ctk_match_v1_CloseSessionRequest__Output, _ctk_match_v1_CloseSessionResponse>;

  DescribeFile: grpc.handleUnaryCall<_ctk_match_v1_DescribeFileRequest__Output, _ctk_match_v1_FileInfo>;

  DescribeResourceScope: grpc.handleUnaryCall<_ctk_match_v1_ResourceScopeRequest__Output, _ctk_match_v1_ResourceScopeInfo>;

  DiscoverFiles: grpc.handleUnaryCall<_ctk_match_v1_DiscoverFilesRequest__Output, _ctk_match_v1_DiscoverFilesResponse>;

  ListFiles: grpc.handleUnaryCall<_ctk_match_v1_ListFilesRequest__Output, _ctk_match_v1_ListFilesResponse>;

  ListSessions: grpc.handleUnaryCall<_ctk_match_v1_ListSessionsRequest__Output, _ctk_match_v1_ListSessionsResponse>;

  Match: grpc.handleUnaryCall<_ctk_match_v1_MatchRequest__Output, _ctk_match_v1_MatchResponse>;

  OpenFile: grpc.handleUnaryCall<_ctk_match_v1_OpenFileRequest__Output, _ctk_match_v1_FileInfo>;

  OpenResourceScope: grpc.handleUnaryCall<_ctk_match_v1_OpenResourceScopeRequest__Output, _ctk_match_v1_ResourceScopeInfo>;

  Parse: grpc.handleUnaryCall<_ctk_match_v1_ParseRequest__Output, _ctk_match_v1_ParseResponse>;

  PruneCaches: grpc.handleUnaryCall<_ctk_match_v1_PruneCachesRequest__Output, _ctk_match_v1_PruneCachesResponse>;

  RefreshFile: grpc.handleUnaryCall<_ctk_match_v1_RefreshFileRequest__Output, _ctk_match_v1_FileInfo>;

  ReleaseResourceScope: grpc.handleUnaryCall<_ctk_match_v1_ResourceScopeRequest__Output, _ctk_match_v1_ResourceScopeInfo>;

  ResourceStatus: grpc.handleUnaryCall<_ctk_match_v1_ResourceStatusRequest__Output, _ctk_match_v1_ResourceStatusResponse>;

  ServerStatus: grpc.handleUnaryCall<_ctk_match_v1_ServerStatusRequest__Output, _ctk_match_v1_ServerStatusResponse>;

  StreamMatch: grpc.handleServerStreamingCall<_ctk_match_v1_MatchRequest__Output, _ctk_match_v1_MatchStreamEvent>;

}

export interface MatchServiceDefinition extends grpc.ServiceDefinition {
  AttachSession: MethodDefinition<_ctk_match_v1_AttachSessionRequest, _ctk_match_v1_SessionInfo, _ctk_match_v1_AttachSessionRequest__Output, _ctk_match_v1_SessionInfo__Output>
  CancelResourceScope: MethodDefinition<_ctk_match_v1_ResourceScopeRequest, _ctk_match_v1_ResourceScopeInfo, _ctk_match_v1_ResourceScopeRequest__Output, _ctk_match_v1_ResourceScopeInfo__Output>
  CloseAllFiles: MethodDefinition<_ctk_match_v1_CloseAllFilesRequest, _ctk_match_v1_CloseFileResponse, _ctk_match_v1_CloseAllFilesRequest__Output, _ctk_match_v1_CloseFileResponse__Output>
  CloseFile: MethodDefinition<_ctk_match_v1_CloseFileRequest, _ctk_match_v1_CloseFileResponse, _ctk_match_v1_CloseFileRequest__Output, _ctk_match_v1_CloseFileResponse__Output>
  CloseSession: MethodDefinition<_ctk_match_v1_CloseSessionRequest, _ctk_match_v1_CloseSessionResponse, _ctk_match_v1_CloseSessionRequest__Output, _ctk_match_v1_CloseSessionResponse__Output>
  DescribeFile: MethodDefinition<_ctk_match_v1_DescribeFileRequest, _ctk_match_v1_FileInfo, _ctk_match_v1_DescribeFileRequest__Output, _ctk_match_v1_FileInfo__Output>
  DescribeResourceScope: MethodDefinition<_ctk_match_v1_ResourceScopeRequest, _ctk_match_v1_ResourceScopeInfo, _ctk_match_v1_ResourceScopeRequest__Output, _ctk_match_v1_ResourceScopeInfo__Output>
  DiscoverFiles: MethodDefinition<_ctk_match_v1_DiscoverFilesRequest, _ctk_match_v1_DiscoverFilesResponse, _ctk_match_v1_DiscoverFilesRequest__Output, _ctk_match_v1_DiscoverFilesResponse__Output>
  ListFiles: MethodDefinition<_ctk_match_v1_ListFilesRequest, _ctk_match_v1_ListFilesResponse, _ctk_match_v1_ListFilesRequest__Output, _ctk_match_v1_ListFilesResponse__Output>
  ListSessions: MethodDefinition<_ctk_match_v1_ListSessionsRequest, _ctk_match_v1_ListSessionsResponse, _ctk_match_v1_ListSessionsRequest__Output, _ctk_match_v1_ListSessionsResponse__Output>
  Match: MethodDefinition<_ctk_match_v1_MatchRequest, _ctk_match_v1_MatchResponse, _ctk_match_v1_MatchRequest__Output, _ctk_match_v1_MatchResponse__Output>
  OpenFile: MethodDefinition<_ctk_match_v1_OpenFileRequest, _ctk_match_v1_FileInfo, _ctk_match_v1_OpenFileRequest__Output, _ctk_match_v1_FileInfo__Output>
  OpenResourceScope: MethodDefinition<_ctk_match_v1_OpenResourceScopeRequest, _ctk_match_v1_ResourceScopeInfo, _ctk_match_v1_OpenResourceScopeRequest__Output, _ctk_match_v1_ResourceScopeInfo__Output>
  Parse: MethodDefinition<_ctk_match_v1_ParseRequest, _ctk_match_v1_ParseResponse, _ctk_match_v1_ParseRequest__Output, _ctk_match_v1_ParseResponse__Output>
  PruneCaches: MethodDefinition<_ctk_match_v1_PruneCachesRequest, _ctk_match_v1_PruneCachesResponse, _ctk_match_v1_PruneCachesRequest__Output, _ctk_match_v1_PruneCachesResponse__Output>
  RefreshFile: MethodDefinition<_ctk_match_v1_RefreshFileRequest, _ctk_match_v1_FileInfo, _ctk_match_v1_RefreshFileRequest__Output, _ctk_match_v1_FileInfo__Output>
  ReleaseResourceScope: MethodDefinition<_ctk_match_v1_ResourceScopeRequest, _ctk_match_v1_ResourceScopeInfo, _ctk_match_v1_ResourceScopeRequest__Output, _ctk_match_v1_ResourceScopeInfo__Output>
  ResourceStatus: MethodDefinition<_ctk_match_v1_ResourceStatusRequest, _ctk_match_v1_ResourceStatusResponse, _ctk_match_v1_ResourceStatusRequest__Output, _ctk_match_v1_ResourceStatusResponse__Output>
  ServerStatus: MethodDefinition<_ctk_match_v1_ServerStatusRequest, _ctk_match_v1_ServerStatusResponse, _ctk_match_v1_ServerStatusRequest__Output, _ctk_match_v1_ServerStatusResponse__Output>
  StreamMatch: MethodDefinition<_ctk_match_v1_MatchRequest, _ctk_match_v1_MatchStreamEvent, _ctk_match_v1_MatchRequest__Output, _ctk_match_v1_MatchStreamEvent__Output>
}
