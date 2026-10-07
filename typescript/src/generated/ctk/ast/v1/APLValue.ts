// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { APLValueBase as _ctk_ast_v1_APLValueBase, APLValueBase__Output as _ctk_ast_v1_APLValueBase__Output } from '../../../ctk/ast/v1/APLValueBase.js';
import type { APLValuePathEntry as _ctk_ast_v1_APLValuePathEntry, APLValuePathEntry__Output as _ctk_ast_v1_APLValuePathEntry__Output } from '../../../ctk/ast/v1/APLValuePathEntry.js';
import type { Long } from '@grpc/proto-loader';

export interface APLValue {
  'base'?: (_ctk_ast_v1_APLValueBase | null);
  'offsetBytes'?: (number | string | Long);
  'path'?: (_ctk_ast_v1_APLValuePathEntry)[];
  'isOnePastEnd'?: (boolean);
  'isNullPointer'?: (boolean);
  '_offsetBytes'?: "offsetBytes";
  '_isOnePastEnd'?: "isOnePastEnd";
  '_isNullPointer'?: "isNullPointer";
}

export interface APLValue__Output {
  'base': (_ctk_ast_v1_APLValueBase__Output | null);
  'offsetBytes'?: (string);
  'path': (_ctk_ast_v1_APLValuePathEntry__Output)[];
  'isOnePastEnd'?: (boolean);
  'isNullPointer'?: (boolean);
  '_offsetBytes'?: "offsetBytes";
  '_isOnePastEnd'?: "isOnePastEnd";
  '_isNullPointer'?: "isNullPointer";
}
