// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface CoawaitExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'operand'?: (_ctk_ast_v1_ExpressionValue | null);
  'readyCall'?: (_ctk_ast_v1_ExpressionValue | null);
  'suspendCall'?: (_ctk_ast_v1_ExpressionValue | null);
  'resumeCall'?: (_ctk_ast_v1_ExpressionValue | null);
  'isReady'?: (boolean);
  '_isReady'?: "isReady";
}

export interface CoawaitExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'operand': (_ctk_ast_v1_ExpressionValue__Output | null);
  'readyCall': (_ctk_ast_v1_ExpressionValue__Output | null);
  'suspendCall': (_ctk_ast_v1_ExpressionValue__Output | null);
  'resumeCall': (_ctk_ast_v1_ExpressionValue__Output | null);
  'isReady'?: (boolean);
  '_isReady'?: "isReady";
}
