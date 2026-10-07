// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';

export interface StmtExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'compoundStatement'?: (_ctk_ast_v1_StatementValue | null);
}

export interface StmtExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'compoundStatement': (_ctk_ast_v1_StatementValue__Output | null);
}
