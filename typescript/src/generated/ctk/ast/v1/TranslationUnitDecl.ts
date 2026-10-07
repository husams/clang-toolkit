// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclInfo as _ctk_ast_v1_DeclInfo, DeclInfo__Output as _ctk_ast_v1_DeclInfo__Output } from '../../../ctk/ast/v1/DeclInfo.js';
import type { DeclarationValue as _ctk_ast_v1_DeclarationValue, DeclarationValue__Output as _ctk_ast_v1_DeclarationValue__Output } from '../../../ctk/ast/v1/DeclarationValue.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';

export interface TranslationUnitDecl {
  'declaration'?: (_ctk_ast_v1_DeclInfo | null);
  'declarations'?: (_ctk_ast_v1_DeclarationValue)[];
  'anonymousNamespace'?: (_ctk_ast_v1_DeclarationSymbol | null);
}

export interface TranslationUnitDecl__Output {
  'declaration': (_ctk_ast_v1_DeclInfo__Output | null);
  'declarations': (_ctk_ast_v1_DeclarationValue__Output)[];
  'anonymousNamespace': (_ctk_ast_v1_DeclarationSymbol__Output | null);
}
