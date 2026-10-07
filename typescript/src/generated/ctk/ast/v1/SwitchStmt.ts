// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclarationValue as _ctk_ast_v1_DeclarationValue, DeclarationValue__Output as _ctk_ast_v1_DeclarationValue__Output } from '../../../ctk/ast/v1/DeclarationValue.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';

export interface SwitchStmt {
  'conditionVariable'?: (_ctk_ast_v1_DeclarationValue | null);
  'condition'?: (_ctk_ast_v1_ExpressionValue | null);
  'body'?: (_ctk_ast_v1_StatementValue | null);
  'defaultCase'?: (_ctk_ast_v1_StatementValue | null);
  'isConstexpr'?: (boolean);
  'isAllEnumCasesCovered'?: (boolean);
  '_isConstexpr'?: "isConstexpr";
  '_isAllEnumCasesCovered'?: "isAllEnumCasesCovered";
}

export interface SwitchStmt__Output {
  'conditionVariable': (_ctk_ast_v1_DeclarationValue__Output | null);
  'condition': (_ctk_ast_v1_ExpressionValue__Output | null);
  'body': (_ctk_ast_v1_StatementValue__Output | null);
  'defaultCase': (_ctk_ast_v1_StatementValue__Output | null);
  'isConstexpr'?: (boolean);
  'isAllEnumCasesCovered'?: (boolean);
  '_isConstexpr'?: "isConstexpr";
  '_isAllEnumCasesCovered'?: "isAllEnumCasesCovered";
}
