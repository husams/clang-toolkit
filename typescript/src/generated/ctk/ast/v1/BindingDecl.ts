// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ValueDeclInfo as _ctk_ast_v1_ValueDeclInfo, ValueDeclInfo__Output as _ctk_ast_v1_ValueDeclInfo__Output } from '../../../ctk/ast/v1/ValueDeclInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface BindingDecl {
  'value'?: (_ctk_ast_v1_ValueDeclInfo | null);
  'holdingVariable'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'binding'?: (_ctk_ast_v1_ExpressionValue | null);
}

export interface BindingDecl__Output {
  'value': (_ctk_ast_v1_ValueDeclInfo__Output | null);
  'holdingVariable': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'binding': (_ctk_ast_v1_ExpressionValue__Output | null);
}
