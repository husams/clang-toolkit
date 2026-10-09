// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_service.proto

import type { Long } from '@grpc/proto-loader';

export interface CacheResources {
  'memoryAvailable'?: (boolean);
  'reusableSnapshots'?: (number | string | Long);
  'reusableMemoryBytes'?: (number | string | Long);
  'pendingBuilds'?: (number | string | Long);
  'storageAvailable'?: (boolean);
  'artifactDiskBytes'?: (number | string | Long);
  'readySnapshots'?: (number | string | Long);
  'staleSnapshots'?: (number | string | Long);
  'leasedSnapshots'?: (number | string | Long);
  'storageRoot'?: (string);
}

export interface CacheResources__Output {
  'memoryAvailable': (boolean);
  'reusableSnapshots': (string);
  'reusableMemoryBytes': (string);
  'pendingBuilds': (string);
  'storageAvailable': (boolean);
  'artifactDiskBytes': (string);
  'readySnapshots': (string);
  'staleSnapshots': (string);
  'leasedSnapshots': (string);
  'storageRoot': (string);
}
