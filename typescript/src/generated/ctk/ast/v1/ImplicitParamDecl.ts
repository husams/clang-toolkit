// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { VarDeclInfo as _ctk_ast_v1_VarDeclInfo, VarDeclInfo__Output as _ctk_ast_v1_VarDeclInfo__Output } from '../../../ctk/ast/v1/VarDeclInfo.js';

export interface ImplicitParamDecl {
  'variable'?: (_ctk_ast_v1_VarDeclInfo | null);
  'parameterIndex'?: (number);
  '_parameterIndex'?: "parameterIndex";
}

export interface ImplicitParamDecl__Output {
  'variable': (_ctk_ast_v1_VarDeclInfo__Output | null);
  'parameterIndex'?: (number);
  '_parameterIndex'?: "parameterIndex";
}
