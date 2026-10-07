// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';

export interface MaterializeTemporaryExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'subexpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'extendingDeclaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'boundToLvalueRank'?: (number);
  '_boundToLvalueRank'?: "boundToLvalueRank";
}

export interface MaterializeTemporaryExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'subexpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'extendingDeclaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'boundToLvalueRank'?: (number);
  '_boundToLvalueRank'?: "boundToLvalueRank";
}
