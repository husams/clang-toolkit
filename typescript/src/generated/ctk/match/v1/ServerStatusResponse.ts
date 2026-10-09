// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_service.proto

import type { CacheResources as _ctk_match_v1_CacheResources, CacheResources__Output as _ctk_match_v1_CacheResources__Output } from '../../../ctk/match/v1/CacheResources.js';
import type { Long } from '@grpc/proto-loader';

export interface ServerStatusResponse {
  'uptimeMs'?: (number | string | Long);
  'residentMemoryBytes'?: (number | string | Long);
  'activeSessions'?: (number | string | Long);
  'retainedMemoryBytes'?: (number | string | Long);
  'maxSessions'?: (number | string | Long);
  'maxRetainedMemoryBytes'?: (number | string | Long);
  'cache'?: (_ctk_match_v1_CacheResources | null);
  '_residentMemoryBytes'?: "residentMemoryBytes";
}

export interface ServerStatusResponse__Output {
  'uptimeMs': (string);
  'residentMemoryBytes'?: (string);
  'activeSessions': (string);
  'retainedMemoryBytes': (string);
  'maxSessions': (string);
  'maxRetainedMemoryBytes': (string);
  'cache': (_ctk_match_v1_CacheResources__Output | null);
  '_residentMemoryBytes'?: "residentMemoryBytes";
}
