// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclInfo as _ctk_ast_v1_DeclInfo, DeclInfo__Output as _ctk_ast_v1_DeclInfo__Output } from '../../../ctk/ast/v1/DeclInfo.js';

export interface ImportDecl {
  'declaration'?: (_ctk_ast_v1_DeclInfo | null);
  'importedModuleName'?: (string);
  '_importedModuleName'?: "importedModuleName";
}

export interface ImportDecl__Output {
  'declaration': (_ctk_ast_v1_DeclInfo__Output | null);
  'importedModuleName'?: (string);
  '_importedModuleName'?: "importedModuleName";
}
