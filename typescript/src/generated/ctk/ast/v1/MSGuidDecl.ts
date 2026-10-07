// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ValueDeclInfo as _ctk_ast_v1_ValueDeclInfo, ValueDeclInfo__Output as _ctk_ast_v1_ValueDeclInfo__Output } from '../../../ctk/ast/v1/ValueDeclInfo.js';
import type { APValue as _ctk_ast_v1_APValue, APValue__Output as _ctk_ast_v1_APValue__Output } from '../../../ctk/ast/v1/APValue.js';

export interface MSGuidDecl {
  'value'?: (_ctk_ast_v1_ValueDeclInfo | null);
  'data1'?: (number);
  'data2'?: (number);
  'data3'?: (number);
  'data4'?: (Buffer | Uint8Array | string);
  'valueAsConstant'?: (_ctk_ast_v1_APValue | null);
  '_data1'?: "data1";
  '_data2'?: "data2";
  '_data3'?: "data3";
  '_data4'?: "data4";
}

export interface MSGuidDecl__Output {
  'value': (_ctk_ast_v1_ValueDeclInfo__Output | null);
  'data1'?: (number);
  'data2'?: (number);
  'data3'?: (number);
  'data4'?: (Buffer);
  'valueAsConstant': (_ctk_ast_v1_APValue__Output | null);
  '_data1'?: "data1";
  '_data2'?: "data2";
  '_data3'?: "data3";
  '_data4'?: "data4";
}
