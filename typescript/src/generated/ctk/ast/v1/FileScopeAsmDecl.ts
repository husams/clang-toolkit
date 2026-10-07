// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclInfo as _ctk_ast_v1_DeclInfo, DeclInfo__Output as _ctk_ast_v1_DeclInfo__Output } from '../../../ctk/ast/v1/DeclInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface FileScopeAsmDecl {
  'declaration'?: (_ctk_ast_v1_DeclInfo | null);
  'assemblyString'?: (_ctk_ast_v1_ExpressionValue | null);
}

export interface FileScopeAsmDecl__Output {
  'declaration': (_ctk_ast_v1_DeclInfo__Output | null);
  'assemblyString': (_ctk_ast_v1_ExpressionValue__Output | null);
}
