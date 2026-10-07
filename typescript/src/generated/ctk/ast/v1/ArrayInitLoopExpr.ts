// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { APIntBits as _ctk_ast_v1_APIntBits, APIntBits__Output as _ctk_ast_v1_APIntBits__Output } from '../../../ctk/ast/v1/APIntBits.js';

export interface ArrayInitLoopExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'commonExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'initializerPerElement'?: (_ctk_ast_v1_ExpressionValue | null);
  'arraySize'?: (_ctk_ast_v1_APIntBits | null);
}

export interface ArrayInitLoopExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'commonExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'initializerPerElement': (_ctk_ast_v1_ExpressionValue__Output | null);
  'arraySize': (_ctk_ast_v1_APIntBits__Output | null);
}
