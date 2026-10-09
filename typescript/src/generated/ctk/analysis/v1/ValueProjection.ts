// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/value_projection.proto

import type { Long } from '@grpc/proto-loader';

// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/value_projection.proto

export const _ctk_analysis_v1_ValueProjection_Mode = {
  MODE_UNSPECIFIED: 'MODE_UNSPECIFIED',
  SHALLOW: 'SHALLOW',
  RECURSIVE: 'RECURSIVE',
} as const;

export type _ctk_analysis_v1_ValueProjection_Mode =
  | 'MODE_UNSPECIFIED'
  | 0
  | 'SHALLOW'
  | 1
  | 'RECURSIVE'
  | 2

export type _ctk_analysis_v1_ValueProjection_Mode__Output = typeof _ctk_analysis_v1_ValueProjection_Mode[keyof typeof _ctk_analysis_v1_ValueProjection_Mode]

export interface ValueProjection {
  'mode'?: (_ctk_analysis_v1_ValueProjection_Mode);
  'maxDepth'?: (number);
  'maxNodes'?: (number | string | Long);
  '_maxDepth'?: "maxDepth";
  '_maxNodes'?: "maxNodes";
}

export interface ValueProjection__Output {
  'mode': (_ctk_analysis_v1_ValueProjection_Mode__Output);
  'maxDepth'?: (number);
  'maxNodes'?: (string);
  '_maxDepth'?: "maxDepth";
  '_maxNodes'?: "maxNodes";
}
