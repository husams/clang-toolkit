// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';

export interface CompoundStmt {
  'body'?: (_ctk_ast_v1_StatementValue)[];
  'isStatementExpression'?: (boolean);
  '_isStatementExpression'?: "isStatementExpression";
}

export interface CompoundStmt__Output {
  'body': (_ctk_ast_v1_StatementValue__Output)[];
  'isStatementExpression'?: (boolean);
  '_isStatementExpression'?: "isStatementExpression";
}
