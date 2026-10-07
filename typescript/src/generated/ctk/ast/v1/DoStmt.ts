// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface DoStmt {
  'body'?: (_ctk_ast_v1_StatementValue | null);
  'condition'?: (_ctk_ast_v1_ExpressionValue | null);
}

export interface DoStmt__Output {
  'body': (_ctk_ast_v1_StatementValue__Output | null);
  'condition': (_ctk_ast_v1_ExpressionValue__Output | null);
}
