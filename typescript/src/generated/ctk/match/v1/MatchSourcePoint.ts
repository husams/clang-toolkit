// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_result.proto

import type { Long } from '@grpc/proto-loader';

export interface MatchSourcePoint {
  'file'?: (string);
  'line'?: (number);
  'column'?: (number);
  'valid'?: (boolean);
  'isMacro'?: (boolean);
  'offset'?: (number | string | Long);
  '_offset'?: "offset";
}

export interface MatchSourcePoint__Output {
  'file': (string);
  'line': (number);
  'column': (number);
  'valid': (boolean);
  'isMacro': (boolean);
  'offset'?: (string);
  '_offset'?: "offset";
}
