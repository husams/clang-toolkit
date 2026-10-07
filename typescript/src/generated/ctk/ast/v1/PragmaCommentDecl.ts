// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclInfo as _ctk_ast_v1_DeclInfo, DeclInfo__Output as _ctk_ast_v1_DeclInfo__Output } from '../../../ctk/ast/v1/DeclInfo.js';
import type { DeclPragmaCommentKind as _ctk_ast_v1_DeclPragmaCommentKind, DeclPragmaCommentKind__Output as _ctk_ast_v1_DeclPragmaCommentKind__Output } from '../../../ctk/ast/v1/DeclPragmaCommentKind.js';

export interface PragmaCommentDecl {
  'declaration'?: (_ctk_ast_v1_DeclInfo | null);
  'commentKind'?: (_ctk_ast_v1_DeclPragmaCommentKind);
  'text'?: (string);
  '_commentKind'?: "commentKind";
  '_text'?: "text";
}

export interface PragmaCommentDecl__Output {
  'declaration': (_ctk_ast_v1_DeclInfo__Output | null);
  'commentKind'?: (_ctk_ast_v1_DeclPragmaCommentKind__Output);
  'text'?: (string);
  '_commentKind'?: "commentKind";
  '_text'?: "text";
}
