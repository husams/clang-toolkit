// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclInfo as _ctk_ast_v1_DeclInfo, DeclInfo__Output as _ctk_ast_v1_DeclInfo__Output } from '../../../ctk/ast/v1/DeclInfo.js';
import type { DeclarationValue as _ctk_ast_v1_DeclarationValue, DeclarationValue__Output as _ctk_ast_v1_DeclarationValue__Output } from '../../../ctk/ast/v1/DeclarationValue.js';

export interface ExportDecl {
  'declaration'?: (_ctk_ast_v1_DeclInfo | null);
  'declarations'?: (_ctk_ast_v1_DeclarationValue)[];
}

export interface ExportDecl__Output {
  'declaration': (_ctk_ast_v1_DeclInfo__Output | null);
  'declarations': (_ctk_ast_v1_DeclarationValue__Output)[];
}
