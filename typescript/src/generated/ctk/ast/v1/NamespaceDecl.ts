// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { NamedDeclInfo as _ctk_ast_v1_NamedDeclInfo, NamedDeclInfo__Output as _ctk_ast_v1_NamedDeclInfo__Output } from '../../../ctk/ast/v1/NamedDeclInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { DeclarationValue as _ctk_ast_v1_DeclarationValue, DeclarationValue__Output as _ctk_ast_v1_DeclarationValue__Output } from '../../../ctk/ast/v1/DeclarationValue.js';

export interface NamespaceDecl {
  'named'?: (_ctk_ast_v1_NamedDeclInfo | null);
  'originalNamespace'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'anonymousNamespace'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'isInline'?: (boolean);
  'isAnonymous'?: (boolean);
  'declarations'?: (_ctk_ast_v1_DeclarationValue)[];
  '_isInline'?: "isInline";
  '_isAnonymous'?: "isAnonymous";
}

export interface NamespaceDecl__Output {
  'named': (_ctk_ast_v1_NamedDeclInfo__Output | null);
  'originalNamespace': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'anonymousNamespace': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'isInline'?: (boolean);
  'isAnonymous'?: (boolean);
  'declarations': (_ctk_ast_v1_DeclarationValue__Output)[];
  '_isInline'?: "isInline";
  '_isAnonymous'?: "isAnonymous";
}
