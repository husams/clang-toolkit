// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { StringLiteralKind as _ctk_ast_v1_StringLiteralKind, StringLiteralKind__Output as _ctk_ast_v1_StringLiteralKind__Output } from '../../../ctk/ast/v1/StringLiteralKind.js';
import type { Long } from '@grpc/proto-loader';

export interface StringLiteral {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'value'?: (Buffer | Uint8Array | string);
  'codeUnitWidth'?: (number);
  'literalKind'?: (_ctk_ast_v1_StringLiteralKind);
  'codeUnitCount'?: (number | string | Long);
  '_value'?: "value";
  '_codeUnitWidth'?: "codeUnitWidth";
  '_literalKind'?: "literalKind";
  '_codeUnitCount'?: "codeUnitCount";
}

export interface StringLiteral__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'value'?: (Buffer);
  'codeUnitWidth'?: (number);
  'literalKind'?: (_ctk_ast_v1_StringLiteralKind__Output);
  'codeUnitCount'?: (string);
  '_value'?: "value";
  '_codeUnitWidth'?: "codeUnitWidth";
  '_literalKind'?: "literalKind";
  '_codeUnitCount'?: "codeUnitCount";
}
