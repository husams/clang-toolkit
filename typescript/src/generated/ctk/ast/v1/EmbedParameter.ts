// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { Long } from '@grpc/proto-loader';

export interface EmbedParameter {
  'name'?: (string);
  'value'?: (number | string | Long);
  '_name'?: "name";
  '_value'?: "value";
}

export interface EmbedParameter__Output {
  'name'?: (string);
  'value'?: (string);
  '_name'?: "name";
  '_value'?: "value";
}
