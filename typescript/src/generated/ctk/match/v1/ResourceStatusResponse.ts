// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/resources.proto

import type { ResourceScopeInfo as _ctk_match_v1_ResourceScopeInfo, ResourceScopeInfo__Output as _ctk_match_v1_ResourceScopeInfo__Output } from '../../../ctk/match/v1/ResourceScopeInfo.js';
import type { Long } from '@grpc/proto-loader';

export interface ResourceStatusResponse {
  'openedInputs'?: (number | string | Long);
  'explicitFileLeases'?: (number | string | Long);
  'resultCursors'?: (number | string | Long);
  'activeWork'?: (number | string | Long);
  'accountedNativeBytes'?: (number | string | Long);
  'reservedBytes'?: (number | string | Long);
  'resultBufferBytes'?: (number | string | Long);
  'queuedWork'?: (number | string | Long);
  'reusableSnapshots'?: (number | string | Long);
  'reusableMemoryBytes'?: (number | string | Long);
  'residentMemoryBytes'?: (number | string | Long);
  'maxInputs'?: (number | string | Long);
  'maxMemoryBytes'?: (number | string | Long);
  'maxResultRows'?: (number | string | Long);
  'maxResultBytes'?: (number | string | Long);
  'maxManifestInputs'?: (number | string | Long);
  'maxManifestBytes'?: (number | string | Long);
  'scopes'?: (_ctk_match_v1_ResourceScopeInfo)[];
  'legacyAccountingSeparate'?: (boolean);
  '_residentMemoryBytes'?: "residentMemoryBytes";
}

export interface ResourceStatusResponse__Output {
  'openedInputs': (string);
  'explicitFileLeases': (string);
  'resultCursors': (string);
  'activeWork': (string);
  'accountedNativeBytes': (string);
  'reservedBytes': (string);
  'resultBufferBytes': (string);
  'queuedWork': (string);
  'reusableSnapshots': (string);
  'reusableMemoryBytes': (string);
  'residentMemoryBytes'?: (string);
  'maxInputs': (string);
  'maxMemoryBytes': (string);
  'maxResultRows': (string);
  'maxResultBytes': (string);
  'maxManifestInputs': (string);
  'maxManifestBytes': (string);
  'scopes': (_ctk_match_v1_ResourceScopeInfo__Output)[];
  'legacyAccountingSeparate': (boolean);
  '_residentMemoryBytes'?: "residentMemoryBytes";
}
