// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';

export interface PackIndexingExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'packExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'packDeclaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'indexExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'selectedIndex'?: (number);
  'selectedExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'substitutedExpressions'?: (_ctk_ast_v1_ExpressionValue)[];
  'isFullySubstituted'?: (boolean);
  '_selectedIndex'?: "selectedIndex";
  '_isFullySubstituted'?: "isFullySubstituted";
}

export interface PackIndexingExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'packExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'packDeclaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'indexExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'selectedIndex'?: (number);
  'selectedExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'substitutedExpressions': (_ctk_ast_v1_ExpressionValue__Output)[];
  'isFullySubstituted'?: (boolean);
  '_selectedIndex'?: "selectedIndex";
  '_isFullySubstituted'?: "isFullySubstituted";
}
