// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/resources.proto

import type { ResourceScopeState as _ctk_match_v1_ResourceScopeState, ResourceScopeState__Output as _ctk_match_v1_ResourceScopeState__Output } from '../../../ctk/match/v1/ResourceScopeState.js';
import type { Timestamp as _google_protobuf_Timestamp, Timestamp__Output as _google_protobuf_Timestamp__Output } from '../../../google/protobuf/Timestamp.js';
import type { Long } from '@grpc/proto-loader';

export interface ResourceScopeInfo {
  'resourceScopeId'?: (string);
  'state'?: (_ctk_match_v1_ResourceScopeState);
  'admittedInputs'?: (number | string | Long);
  'reservedBytes'?: (number | string | Long);
  'accountedNativeBytes'?: (number | string | Long);
  'fileLeases'?: (number | string | Long);
  'resultCursors'?: (number | string | Long);
  'activeWork'?: (number | string | Long);
  'resultBufferBytes'?: (number | string | Long);
  'memoryLimitBytes'?: (number | string | Long);
  'jobs'?: (number);
  'transient'?: (boolean);
  'expiresAt'?: (_google_protobuf_Timestamp | null);
  'cleanupAcknowledged'?: (boolean);
  'peakAccountedBytes'?: (number | string | Long);
  'peakReservedBytes'?: (number | string | Long);
}

export interface ResourceScopeInfo__Output {
  'resourceScopeId': (string);
  'state': (_ctk_match_v1_ResourceScopeState__Output);
  'admittedInputs': (string);
  'reservedBytes': (string);
  'accountedNativeBytes': (string);
  'fileLeases': (string);
  'resultCursors': (string);
  'activeWork': (string);
  'resultBufferBytes': (string);
  'memoryLimitBytes': (string);
  'jobs': (number);
  'transient': (boolean);
  'expiresAt': (_google_protobuf_Timestamp__Output | null);
  'cleanupAcknowledged': (boolean);
  'peakAccountedBytes': (string);
  'peakReservedBytes': (string);
}
