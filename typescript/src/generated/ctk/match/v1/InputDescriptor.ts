// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/resources.proto

import type { CompilationProfile as _ctk_match_v1_CompilationProfile, CompilationProfile__Output as _ctk_match_v1_CompilationProfile__Output } from '../../../ctk/match/v1/CompilationProfile.js';
import type { Long } from '@grpc/proto-loader';

export interface InputDescriptor {
  'filePath'?: (string);
  'profile'?: (_ctk_match_v1_CompilationProfile | null);
  'sourceBytes'?: (number | string | Long);
  'estimatedParseBytes'?: (number | string | Long);
}

export interface InputDescriptor__Output {
  'filePath': (string);
  'profile': (_ctk_match_v1_CompilationProfile__Output | null);
  'sourceBytes': (string);
  'estimatedParseBytes': (string);
}
