// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclInfo as _ctk_ast_v1_DeclInfo, DeclInfo__Output as _ctk_ast_v1_DeclInfo__Output } from '../../../ctk/ast/v1/DeclInfo.js';
import type { DeclarationName as _ctk_ast_v1_DeclarationName, DeclarationName__Output as _ctk_ast_v1_DeclarationName__Output } from '../../../ctk/ast/v1/DeclarationName.js';

export interface NamedDeclInfo {
  'declaration'?: (_ctk_ast_v1_DeclInfo | null);
  'name'?: (_ctk_ast_v1_DeclarationName | null);
  'qualifiedName'?: (string);
  '_qualifiedName'?: "qualifiedName";
}

export interface NamedDeclInfo__Output {
  'declaration': (_ctk_ast_v1_DeclInfo__Output | null);
  'name': (_ctk_ast_v1_DeclarationName__Output | null);
  'qualifiedName'?: (string);
  '_qualifiedName'?: "qualifiedName";
}
