// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { CallExprInfo as _ctk_ast_v1_CallExprInfo, CallExprInfo__Output as _ctk_ast_v1_CallExprInfo__Output } from '../../../ctk/ast/v1/CallExprInfo.js';
import type { OverloadedOperatorKind as _ctk_ast_v1_OverloadedOperatorKind, OverloadedOperatorKind__Output as _ctk_ast_v1_OverloadedOperatorKind__Output } from '../../../ctk/ast/v1/OverloadedOperatorKind.js';

export interface CXXOperatorCallExpr {
  'call'?: (_ctk_ast_v1_CallExprInfo | null);
  'operatorKind'?: (_ctk_ast_v1_OverloadedOperatorKind);
  '_operatorKind'?: "operatorKind";
}

export interface CXXOperatorCallExpr__Output {
  'call': (_ctk_ast_v1_CallExprInfo__Output | null);
  'operatorKind'?: (_ctk_ast_v1_OverloadedOperatorKind__Output);
  '_operatorKind'?: "operatorKind";
}
