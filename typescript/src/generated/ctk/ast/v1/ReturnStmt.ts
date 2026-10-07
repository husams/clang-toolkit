// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';

export interface ReturnStmt {
  'returnValue'?: (_ctk_ast_v1_ExpressionValue | null);
  'returnValueInit'?: (_ctk_ast_v1_ExpressionValue | null);
  'nrvoCandidate'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'isNoreturn'?: (boolean);
  '_isNoreturn'?: "isNoreturn";
}

export interface ReturnStmt__Output {
  'returnValue': (_ctk_ast_v1_ExpressionValue__Output | null);
  'returnValueInit': (_ctk_ast_v1_ExpressionValue__Output | null);
  'nrvoCandidate': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'isNoreturn'?: (boolean);
  '_isNoreturn'?: "isNoreturn";
}
