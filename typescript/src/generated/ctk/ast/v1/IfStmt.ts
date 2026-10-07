// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';
import type { DeclarationValue as _ctk_ast_v1_DeclarationValue, DeclarationValue__Output as _ctk_ast_v1_DeclarationValue__Output } from '../../../ctk/ast/v1/DeclarationValue.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface IfStmt {
  'initStatement'?: (_ctk_ast_v1_StatementValue | null);
  'conditionVariable'?: (_ctk_ast_v1_DeclarationValue | null);
  'condition'?: (_ctk_ast_v1_ExpressionValue | null);
  'thenStatement'?: (_ctk_ast_v1_StatementValue | null);
  'elseStatement'?: (_ctk_ast_v1_StatementValue | null);
  'isConstexpr'?: (boolean);
  'isNegatedCondition'?: (boolean);
  'isConsteval'?: (boolean);
  '_isConstexpr'?: "isConstexpr";
  '_isNegatedCondition'?: "isNegatedCondition";
  '_isConsteval'?: "isConsteval";
}

export interface IfStmt__Output {
  'initStatement': (_ctk_ast_v1_StatementValue__Output | null);
  'conditionVariable': (_ctk_ast_v1_DeclarationValue__Output | null);
  'condition': (_ctk_ast_v1_ExpressionValue__Output | null);
  'thenStatement': (_ctk_ast_v1_StatementValue__Output | null);
  'elseStatement': (_ctk_ast_v1_StatementValue__Output | null);
  'isConstexpr'?: (boolean);
  'isNegatedCondition'?: (boolean);
  'isConsteval'?: (boolean);
  '_isConstexpr'?: "isConstexpr";
  '_isNegatedCondition'?: "isNegatedCondition";
  '_isConsteval'?: "isConsteval";
}
