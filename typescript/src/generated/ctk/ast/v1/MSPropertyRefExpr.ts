// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';

export interface MSPropertyRefExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'base'?: (_ctk_ast_v1_ExpressionValue | null);
  'property'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'isArrow'?: (boolean);
  '_isArrow'?: "isArrow";
}

export interface MSPropertyRefExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'base': (_ctk_ast_v1_ExpressionValue__Output | null);
  'property': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'isArrow'?: (boolean);
  '_isArrow'?: "isArrow";
}
