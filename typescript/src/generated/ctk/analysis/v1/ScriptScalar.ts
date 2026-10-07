// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/script_scalar.proto

import type { Long } from '@grpc/proto-loader';

export interface ScriptScalar {
  'text'?: (string);
  'integer'?: (number | string | Long);
  'number'?: (number | string);
  'boolean'?: (boolean);
  'value'?: "text"|"integer"|"number"|"boolean";
}

export interface ScriptScalar__Output {
  'text'?: (string);
  'integer'?: (string);
  'number'?: (number);
  'boolean'?: (boolean);
  'value'?: "text"|"integer"|"number"|"boolean";
}
