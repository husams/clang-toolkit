// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/resources.proto

import type { InputDescriptor as _ctk_match_v1_InputDescriptor, InputDescriptor__Output as _ctk_match_v1_InputDescriptor__Output } from '../../../ctk/match/v1/InputDescriptor.js';
import type { FileState as _ctk_match_v1_FileState, FileState__Output as _ctk_match_v1_FileState__Output } from '../../../ctk/match/v1/FileState.js';
import type { Timestamp as _google_protobuf_Timestamp, Timestamp__Output as _google_protobuf_Timestamp__Output } from '../../../google/protobuf/Timestamp.js';
import type { Long } from '@grpc/proto-loader';

export interface FileInfo {
  'leaseId'?: (string);
  'input'?: (_ctk_match_v1_InputDescriptor | null);
  'snapshotId'?: (string);
  'sourceRevision'?: (string);
  'explicitLeases'?: (number | string | Long);
  'cursorCount'?: (number | string | Long);
  'activeWork'?: (number | string | Long);
  'accountedNativeBytes'?: (number | string | Long);
  'state'?: (_ctk_match_v1_FileState);
  'sessionIds'?: (string)[];
  'resourceScopeId'?: (string);
  'expiresAt'?: (_google_protobuf_Timestamp | null);
  'rootSessionId'?: (string);
}

export interface FileInfo__Output {
  'leaseId': (string);
  'input': (_ctk_match_v1_InputDescriptor__Output | null);
  'snapshotId': (string);
  'sourceRevision': (string);
  'explicitLeases': (string);
  'cursorCount': (string);
  'activeWork': (string);
  'accountedNativeBytes': (string);
  'state': (_ctk_match_v1_FileState__Output);
  'sessionIds': (string)[];
  'resourceScopeId': (string);
  'expiresAt': (_google_protobuf_Timestamp__Output | null);
  'rootSessionId': (string);
}
