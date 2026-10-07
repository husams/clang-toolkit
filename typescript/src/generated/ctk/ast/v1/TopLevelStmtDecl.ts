// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclInfo as _ctk_ast_v1_DeclInfo, DeclInfo__Output as _ctk_ast_v1_DeclInfo__Output } from '../../../ctk/ast/v1/DeclInfo.js';
import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';

export interface TopLevelStmtDecl {
  'declaration'?: (_ctk_ast_v1_DeclInfo | null);
  'statement'?: (_ctk_ast_v1_StatementValue | null);
}

export interface TopLevelStmtDecl__Output {
  'declaration': (_ctk_ast_v1_DeclInfo__Output | null);
  'statement': (_ctk_ast_v1_StatementValue__Output | null);
}
