// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { APValue as _ctk_ast_v1_APValue, APValue__Output as _ctk_ast_v1_APValue__Output } from '../../../ctk/ast/v1/APValue.js';
import type { ConstantExprResult as _ctk_ast_v1_ConstantExprResult, ConstantExprResult__Output as _ctk_ast_v1_ConstantExprResult__Output } from '../../../ctk/ast/v1/ConstantExprResult.js';

export interface ConstantExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'subexpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'value'?: (_ctk_ast_v1_APValue | null);
  'resultKind'?: (_ctk_ast_v1_ConstantExprResult);
  '_resultKind'?: "resultKind";
}

export interface ConstantExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'subexpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'value': (_ctk_ast_v1_APValue__Output | null);
  'resultKind'?: (_ctk_ast_v1_ConstantExprResult__Output);
  '_resultKind'?: "resultKind";
}
