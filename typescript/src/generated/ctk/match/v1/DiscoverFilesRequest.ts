// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/resources.proto

import type { CompilationProfile as _ctk_match_v1_CompilationProfile, CompilationProfile__Output as _ctk_match_v1_CompilationProfile__Output } from '../../../ctk/match/v1/CompilationProfile.js';
import type { InputDescriptor as _ctk_match_v1_InputDescriptor, InputDescriptor__Output as _ctk_match_v1_InputDescriptor__Output } from '../../../ctk/match/v1/InputDescriptor.js';
import type { Long } from '@grpc/proto-loader';

export interface DiscoverFilesRequest {
  'paths'?: (string)[];
  'profile'?: (_ctk_match_v1_CompilationProfile | null);
  'inputs'?: (_ctk_match_v1_InputDescriptor)[];
  'maxInputs'?: (number | string | Long);
  'maxMetadataBytes'?: (number | string | Long);
  '_maxInputs'?: "maxInputs";
  '_maxMetadataBytes'?: "maxMetadataBytes";
}

export interface DiscoverFilesRequest__Output {
  'paths': (string)[];
  'profile': (_ctk_match_v1_CompilationProfile__Output | null);
  'inputs': (_ctk_match_v1_InputDescriptor__Output)[];
  'maxInputs'?: (string);
  'maxMetadataBytes'?: (string);
  '_maxInputs'?: "maxInputs";
  '_maxMetadataBytes'?: "maxMetadataBytes";
}
