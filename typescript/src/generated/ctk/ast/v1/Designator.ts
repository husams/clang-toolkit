// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface Designator {
  'fieldDeclaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'arrayIndex'?: (_ctk_ast_v1_ExpressionValue | null);
  'arrayRangeStart'?: (_ctk_ast_v1_ExpressionValue | null);
  'arrayRangeEnd'?: (_ctk_ast_v1_ExpressionValue | null);
  'kind'?: "fieldDeclaration"|"arrayIndex"|"arrayRangeStart";
}

export interface Designator__Output {
  'fieldDeclaration'?: (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'arrayIndex'?: (_ctk_ast_v1_ExpressionValue__Output | null);
  'arrayRangeStart'?: (_ctk_ast_v1_ExpressionValue__Output | null);
  'arrayRangeEnd': (_ctk_ast_v1_ExpressionValue__Output | null);
  'kind'?: "fieldDeclaration"|"arrayIndex"|"arrayRangeStart";
}
