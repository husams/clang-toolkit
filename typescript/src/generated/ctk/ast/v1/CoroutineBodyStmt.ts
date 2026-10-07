// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';
import type { DeclarationValue as _ctk_ast_v1_DeclarationValue, DeclarationValue__Output as _ctk_ast_v1_DeclarationValue__Output } from '../../../ctk/ast/v1/DeclarationValue.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface CoroutineBodyStmt {
  'body'?: (_ctk_ast_v1_StatementValue | null);
  'promiseDeclaration'?: (_ctk_ast_v1_DeclarationValue | null);
  'returnValue'?: (_ctk_ast_v1_ExpressionValue | null);
  'exceptionHandler'?: (_ctk_ast_v1_StatementValue | null);
  'fallthroughHandler'?: (_ctk_ast_v1_StatementValue | null);
  'parameterMoves'?: (_ctk_ast_v1_StatementValue)[];
  'allocationExpressions'?: (_ctk_ast_v1_ExpressionValue)[];
  'deallocationExpressions'?: (_ctk_ast_v1_ExpressionValue)[];
}

export interface CoroutineBodyStmt__Output {
  'body': (_ctk_ast_v1_StatementValue__Output | null);
  'promiseDeclaration': (_ctk_ast_v1_DeclarationValue__Output | null);
  'returnValue': (_ctk_ast_v1_ExpressionValue__Output | null);
  'exceptionHandler': (_ctk_ast_v1_StatementValue__Output | null);
  'fallthroughHandler': (_ctk_ast_v1_StatementValue__Output | null);
  'parameterMoves': (_ctk_ast_v1_StatementValue__Output)[];
  'allocationExpressions': (_ctk_ast_v1_ExpressionValue__Output)[];
  'deallocationExpressions': (_ctk_ast_v1_ExpressionValue__Output)[];
}
