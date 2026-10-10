// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/resources.proto

import type { InputDescriptor as _ctk_match_v1_InputDescriptor, InputDescriptor__Output as _ctk_match_v1_InputDescriptor__Output } from '../../../ctk/match/v1/InputDescriptor.js';
import type { Long } from '@grpc/proto-loader';

export interface DiscoverFilesResponse {
  'inputs'?: (_ctk_match_v1_InputDescriptor)[];
  'diagnostics'?: (string)[];
  'metadataBytes'?: (number | string | Long);
}

export interface DiscoverFilesResponse__Output {
  'inputs': (_ctk_match_v1_InputDescriptor__Output)[];
  'diagnostics': (string)[];
  'metadataBytes': (string);
}
