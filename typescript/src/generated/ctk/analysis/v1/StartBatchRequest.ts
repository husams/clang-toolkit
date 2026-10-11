// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/batch.proto

import type { InputDescriptor as _ctk_match_v1_InputDescriptor, InputDescriptor__Output as _ctk_match_v1_InputDescriptor__Output } from '../../../ctk/match/v1/InputDescriptor.js';
import type { Long } from '@grpc/proto-loader';

export interface StartBatchRequest {
  'requestId'?: (string);
  'inputs'?: (_ctk_match_v1_InputDescriptor)[];
  'bodySource'?: (string);
  'groupVariable'?: (string);
  'size'?: (number);
  'count'?: (number);
  'jobs'?: (number);
  'memoryBytes'?: (number | string | Long);
  'continueOnError'?: (boolean);
  'partition'?: "size"|"count";
  '_jobs'?: "jobs";
  '_memoryBytes'?: "memoryBytes";
}

export interface StartBatchRequest__Output {
  'requestId': (string);
  'inputs': (_ctk_match_v1_InputDescriptor__Output)[];
  'bodySource': (string);
  'groupVariable': (string);
  'size'?: (number);
  'count'?: (number);
  'jobs'?: (number);
  'memoryBytes'?: (string);
  'continueOnError': (boolean);
  'partition'?: "size"|"count";
  '_jobs'?: "jobs";
  '_memoryBytes'?: "memoryBytes";
}
