// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { VarDeclInfo as _ctk_ast_v1_VarDeclInfo, VarDeclInfo__Output as _ctk_ast_v1_VarDeclInfo__Output } from '../../../ctk/ast/v1/VarDeclInfo.js';
import type { DeclarationValue as _ctk_ast_v1_DeclarationValue, DeclarationValue__Output as _ctk_ast_v1_DeclarationValue__Output } from '../../../ctk/ast/v1/DeclarationValue.js';

export interface DecompositionDecl {
  'variable'?: (_ctk_ast_v1_VarDeclInfo | null);
  'bindings'?: (_ctk_ast_v1_DeclarationValue)[];
}

export interface DecompositionDecl__Output {
  'variable': (_ctk_ast_v1_VarDeclInfo__Output | null);
  'bindings': (_ctk_ast_v1_DeclarationValue__Output)[];
}
