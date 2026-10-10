// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/batch.proto

import type { Long } from '@grpc/proto-loader';

export interface BatchControlRequest {
  'runId'?: (string);
  'expectedRevision'?: (number | string | Long);
}

export interface BatchControlRequest__Output {
  'runId': (string);
  'expectedRevision': (string);
}
