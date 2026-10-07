// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';

export interface SEHExceptStmt {
  'filterExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'block'?: (_ctk_ast_v1_StatementValue | null);
}

export interface SEHExceptStmt__Output {
  'filterExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'block': (_ctk_ast_v1_StatementValue__Output | null);
}
