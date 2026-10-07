// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclInfo as _ctk_ast_v1_DeclInfo, DeclInfo__Output as _ctk_ast_v1_DeclInfo__Output } from '../../../ctk/ast/v1/DeclInfo.js';
import type { AccessSpecifier as _ctk_ast_v1_AccessSpecifier, AccessSpecifier__Output as _ctk_ast_v1_AccessSpecifier__Output } from '../../../ctk/ast/v1/AccessSpecifier.js';

export interface AccessSpecDecl {
  'declaration'?: (_ctk_ast_v1_DeclInfo | null);
  'access'?: (_ctk_ast_v1_AccessSpecifier);
  '_access'?: "access";
}

export interface AccessSpecDecl__Output {
  'declaration': (_ctk_ast_v1_DeclInfo__Output | null);
  'access'?: (_ctk_ast_v1_AccessSpecifier__Output);
  '_access'?: "access";
}
