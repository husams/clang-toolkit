// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { VarDeclInfo as _ctk_ast_v1_VarDeclInfo, VarDeclInfo__Output as _ctk_ast_v1_VarDeclInfo__Output } from '../../../ctk/ast/v1/VarDeclInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface ParmVarDecl {
  'variable'?: (_ctk_ast_v1_VarDeclInfo | null);
  'defaultArgument'?: (_ctk_ast_v1_ExpressionValue | null);
  'functionScopeIndex'?: (number);
  'functionScopeDepth'?: (number);
  'isParameterPack'?: (boolean);
  'isExplicitObjectParameter'?: (boolean);
  '_functionScopeIndex'?: "functionScopeIndex";
  '_functionScopeDepth'?: "functionScopeDepth";
  '_isParameterPack'?: "isParameterPack";
  '_isExplicitObjectParameter'?: "isExplicitObjectParameter";
}

export interface ParmVarDecl__Output {
  'variable': (_ctk_ast_v1_VarDeclInfo__Output | null);
  'defaultArgument': (_ctk_ast_v1_ExpressionValue__Output | null);
  'functionScopeIndex'?: (number);
  'functionScopeDepth'?: (number);
  'isParameterPack'?: (boolean);
  'isExplicitObjectParameter'?: (boolean);
  '_functionScopeIndex'?: "functionScopeIndex";
  '_functionScopeDepth'?: "functionScopeDepth";
  '_isParameterPack'?: "isParameterPack";
  '_isExplicitObjectParameter'?: "isExplicitObjectParameter";
}
