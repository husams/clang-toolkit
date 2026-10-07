// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';

export interface CXXTryStmt {
  'tryBlock'?: (_ctk_ast_v1_StatementValue | null);
  'handlers'?: (_ctk_ast_v1_StatementValue)[];
}

export interface CXXTryStmt__Output {
  'tryBlock': (_ctk_ast_v1_StatementValue__Output | null);
  'handlers': (_ctk_ast_v1_StatementValue__Output)[];
}
