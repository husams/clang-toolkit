// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclaratorDeclInfo as _ctk_ast_v1_DeclaratorDeclInfo, DeclaratorDeclInfo__Output as _ctk_ast_v1_DeclaratorDeclInfo__Output } from '../../../ctk/ast/v1/DeclaratorDeclInfo.js';

export interface MSPropertyDecl {
  'declarator'?: (_ctk_ast_v1_DeclaratorDeclInfo | null);
  'getterIdentifier'?: (string);
  'setterIdentifier'?: (string);
  '_getterIdentifier'?: "getterIdentifier";
  '_setterIdentifier'?: "setterIdentifier";
}

export interface MSPropertyDecl__Output {
  'declarator': (_ctk_ast_v1_DeclaratorDeclInfo__Output | null);
  'getterIdentifier'?: (string);
  'setterIdentifier'?: (string);
  '_getterIdentifier'?: "getterIdentifier";
  '_setterIdentifier'?: "setterIdentifier";
}
