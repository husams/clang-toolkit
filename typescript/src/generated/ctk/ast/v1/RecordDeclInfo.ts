// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TagDeclInfo as _ctk_ast_v1_TagDeclInfo, TagDeclInfo__Output as _ctk_ast_v1_TagDeclInfo__Output } from '../../../ctk/ast/v1/TagDeclInfo.js';
import type { DeclarationValue as _ctk_ast_v1_DeclarationValue, DeclarationValue__Output as _ctk_ast_v1_DeclarationValue__Output } from '../../../ctk/ast/v1/DeclarationValue.js';

export interface RecordDeclInfo {
  'tag'?: (_ctk_ast_v1_TagDeclInfo | null);
  'members'?: (_ctk_ast_v1_DeclarationValue)[];
}

export interface RecordDeclInfo__Output {
  'tag': (_ctk_ast_v1_TagDeclInfo__Output | null);
  'members': (_ctk_ast_v1_DeclarationValue__Output)[];
}
