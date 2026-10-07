// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { NestedNameSpecifier as _ctk_ast_v1_NestedNameSpecifier, NestedNameSpecifier__Output as _ctk_ast_v1_NestedNameSpecifier__Output } from '../../../ctk/ast/v1/NestedNameSpecifier.js';

export interface NestedNamespaceName {
  'declaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'prefix'?: (_ctk_ast_v1_NestedNameSpecifier | null);
}

export interface NestedNamespaceName__Output {
  'declaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'prefix': (_ctk_ast_v1_NestedNameSpecifier__Output | null);
}
