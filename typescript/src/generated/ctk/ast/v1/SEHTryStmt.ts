// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';

export interface SEHTryStmt {
  'tryBlock'?: (_ctk_ast_v1_StatementValue | null);
  'handler'?: (_ctk_ast_v1_StatementValue | null);
  'isCxxTry'?: (boolean);
  '_isCxxTry'?: "isCxxTry";
}

export interface SEHTryStmt__Output {
  'tryBlock': (_ctk_ast_v1_StatementValue__Output | null);
  'handler': (_ctk_ast_v1_StatementValue__Output | null);
  'isCxxTry'?: (boolean);
  '_isCxxTry'?: "isCxxTry";
}
