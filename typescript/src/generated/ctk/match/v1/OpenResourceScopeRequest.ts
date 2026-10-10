// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/resources.proto

import type { InputDescriptor as _ctk_match_v1_InputDescriptor, InputDescriptor__Output as _ctk_match_v1_InputDescriptor__Output } from '../../../ctk/match/v1/InputDescriptor.js';
import type { Long } from '@grpc/proto-loader';

export interface OpenResourceScopeRequest {
  'inputs'?: (_ctk_match_v1_InputDescriptor)[];
  'memoryBytes'?: (number | string | Long);
  'jobs'?: (number);
  'transient'?: (boolean);
  'ttlMs'?: (number | string | Long);
  '_memoryBytes'?: "memoryBytes";
  '_jobs'?: "jobs";
  '_ttlMs'?: "ttlMs";
}

export interface OpenResourceScopeRequest__Output {
  'inputs': (_ctk_match_v1_InputDescriptor__Output)[];
  'memoryBytes'?: (string);
  'jobs'?: (number);
  'transient': (boolean);
  'ttlMs'?: (string);
  '_memoryBytes'?: "memoryBytes";
  '_jobs'?: "jobs";
  '_ttlMs'?: "ttlMs";
}
