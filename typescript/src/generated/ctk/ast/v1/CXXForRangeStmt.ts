// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';
import type { DeclarationValue as _ctk_ast_v1_DeclarationValue, DeclarationValue__Output as _ctk_ast_v1_DeclarationValue__Output } from '../../../ctk/ast/v1/DeclarationValue.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface CXXForRangeStmt {
  'initStatement'?: (_ctk_ast_v1_StatementValue | null);
  'loopVariable'?: (_ctk_ast_v1_DeclarationValue | null);
  'rangeStatement'?: (_ctk_ast_v1_StatementValue | null);
  'beginStatement'?: (_ctk_ast_v1_StatementValue | null);
  'endStatement'?: (_ctk_ast_v1_StatementValue | null);
  'condition'?: (_ctk_ast_v1_ExpressionValue | null);
  'increment'?: (_ctk_ast_v1_ExpressionValue | null);
  'body'?: (_ctk_ast_v1_StatementValue | null);
  'isForRangeLoop'?: (boolean);
  '_isForRangeLoop'?: "isForRangeLoop";
}

export interface CXXForRangeStmt__Output {
  'initStatement': (_ctk_ast_v1_StatementValue__Output | null);
  'loopVariable': (_ctk_ast_v1_DeclarationValue__Output | null);
  'rangeStatement': (_ctk_ast_v1_StatementValue__Output | null);
  'beginStatement': (_ctk_ast_v1_StatementValue__Output | null);
  'endStatement': (_ctk_ast_v1_StatementValue__Output | null);
  'condition': (_ctk_ast_v1_ExpressionValue__Output | null);
  'increment': (_ctk_ast_v1_ExpressionValue__Output | null);
  'body': (_ctk_ast_v1_StatementValue__Output | null);
  'isForRangeLoop'?: (boolean);
  '_isForRangeLoop'?: "isForRangeLoop";
}
