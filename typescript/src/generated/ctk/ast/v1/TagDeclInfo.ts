// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeDeclInfo as _ctk_ast_v1_TypeDeclInfo, TypeDeclInfo__Output as _ctk_ast_v1_TypeDeclInfo__Output } from '../../../ctk/ast/v1/TypeDeclInfo.js';
import type { TagKind as _ctk_ast_v1_TagKind, TagKind__Output as _ctk_ast_v1_TagKind__Output } from '../../../ctk/ast/v1/TagKind.js';

export interface TagDeclInfo {
  'typeDeclaration'?: (_ctk_ast_v1_TypeDeclInfo | null);
  'tagKind'?: (_ctk_ast_v1_TagKind);
  'isCompleteDefinition'?: (boolean);
  '_tagKind'?: "tagKind";
  '_isCompleteDefinition'?: "isCompleteDefinition";
}

export interface TagDeclInfo__Output {
  'typeDeclaration': (_ctk_ast_v1_TypeDeclInfo__Output | null);
  'tagKind'?: (_ctk_ast_v1_TagKind__Output);
  'isCompleteDefinition'?: (boolean);
  '_tagKind'?: "tagKind";
  '_isCompleteDefinition'?: "isCompleteDefinition";
}
