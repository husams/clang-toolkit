// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TagDeclInfo as _ctk_ast_v1_TagDeclInfo, TagDeclInfo__Output as _ctk_ast_v1_TagDeclInfo__Output } from '../../../ctk/ast/v1/TagDeclInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';

export interface EnumDecl {
  'tag'?: (_ctk_ast_v1_TagDeclInfo | null);
  'integerType'?: (_ctk_ast_v1_QualType | null);
  'promotionType'?: (_ctk_ast_v1_QualType | null);
  'isScoped'?: (boolean);
  'isFixed'?: (boolean);
  '_isScoped'?: "isScoped";
  '_isFixed'?: "isFixed";
}

export interface EnumDecl__Output {
  'tag': (_ctk_ast_v1_TagDeclInfo__Output | null);
  'integerType': (_ctk_ast_v1_QualType__Output | null);
  'promotionType': (_ctk_ast_v1_QualType__Output | null);
  'isScoped'?: (boolean);
  'isFixed'?: (boolean);
  '_isScoped'?: "isScoped";
  '_isFixed'?: "isFixed";
}
