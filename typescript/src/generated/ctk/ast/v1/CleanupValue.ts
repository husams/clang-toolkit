// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface CleanupValue {
  'block'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'compoundLiteral'?: (_ctk_ast_v1_ExpressionValue | null);
  'value'?: "block"|"compoundLiteral";
}

export interface CleanupValue__Output {
  'block'?: (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'compoundLiteral'?: (_ctk_ast_v1_ExpressionValue__Output | null);
  'value'?: "block"|"compoundLiteral";
}
