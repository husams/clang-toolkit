// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { DeclarationValue as _ctk_ast_v1_DeclarationValue, DeclarationValue__Output as _ctk_ast_v1_DeclarationValue__Output } from '../../../ctk/ast/v1/DeclarationValue.js';

export interface BlockExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'blockDeclaration'?: (_ctk_ast_v1_DeclarationValue | null);
}

export interface BlockExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'blockDeclaration': (_ctk_ast_v1_DeclarationValue__Output | null);
}
