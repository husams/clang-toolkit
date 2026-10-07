// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { UsingShadowDecl as _ctk_ast_v1_UsingShadowDecl, UsingShadowDecl__Output as _ctk_ast_v1_UsingShadowDecl__Output } from '../../../ctk/ast/v1/UsingShadowDecl.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';

export interface ConstructorUsingShadowDecl {
  'usingShadow'?: (_ctk_ast_v1_UsingShadowDecl | null);
  'nominatedBaseClass'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'constructedBaseClass'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'constructsVirtualBase'?: (boolean);
  '_constructsVirtualBase'?: "constructsVirtualBase";
}

export interface ConstructorUsingShadowDecl__Output {
  'usingShadow': (_ctk_ast_v1_UsingShadowDecl__Output | null);
  'nominatedBaseClass': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'constructedBaseClass': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'constructsVirtualBase'?: (boolean);
  '_constructsVirtualBase'?: "constructsVirtualBase";
}
