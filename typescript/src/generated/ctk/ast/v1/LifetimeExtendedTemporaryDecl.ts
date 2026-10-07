// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclInfo as _ctk_ast_v1_DeclInfo, DeclInfo__Output as _ctk_ast_v1_DeclInfo__Output } from '../../../ctk/ast/v1/DeclInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface LifetimeExtendedTemporaryDecl {
  'declaration'?: (_ctk_ast_v1_DeclInfo | null);
  'extendingDeclaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'temporaryExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'manglingNumber'?: (number);
  '_manglingNumber'?: "manglingNumber";
}

export interface LifetimeExtendedTemporaryDecl__Output {
  'declaration': (_ctk_ast_v1_DeclInfo__Output | null);
  'extendingDeclaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'temporaryExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'manglingNumber'?: (number);
  '_manglingNumber'?: "manglingNumber";
}
