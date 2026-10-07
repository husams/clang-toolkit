// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclInfo as _ctk_ast_v1_DeclInfo, DeclInfo__Output as _ctk_ast_v1_DeclInfo__Output } from '../../../ctk/ast/v1/DeclInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';

export interface FriendDecl {
  'declaration'?: (_ctk_ast_v1_DeclInfo | null);
  'friendDeclaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'friendType'?: (_ctk_ast_v1_QualType | null);
  'isPackExpansion'?: (boolean);
  '_isPackExpansion'?: "isPackExpansion";
}

export interface FriendDecl__Output {
  'declaration': (_ctk_ast_v1_DeclInfo__Output | null);
  'friendDeclaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'friendType': (_ctk_ast_v1_QualType__Output | null);
  'isPackExpansion'?: (boolean);
  '_isPackExpansion'?: "isPackExpansion";
}
