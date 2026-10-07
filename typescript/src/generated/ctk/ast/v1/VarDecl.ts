// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { VarDeclInfo as _ctk_ast_v1_VarDeclInfo, VarDeclInfo__Output as _ctk_ast_v1_VarDeclInfo__Output } from '../../../ctk/ast/v1/VarDeclInfo.js';
import type { DeclVariableTLSKind as _ctk_ast_v1_DeclVariableTLSKind, DeclVariableTLSKind__Output as _ctk_ast_v1_DeclVariableTLSKind__Output } from '../../../ctk/ast/v1/DeclVariableTLSKind.js';
import type { DeclVariableInitializationStyle as _ctk_ast_v1_DeclVariableInitializationStyle, DeclVariableInitializationStyle__Output as _ctk_ast_v1_DeclVariableInitializationStyle__Output } from '../../../ctk/ast/v1/DeclVariableInitializationStyle.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface VarDecl {
  'variable'?: (_ctk_ast_v1_VarDeclInfo | null);
  'tlsKind'?: (_ctk_ast_v1_DeclVariableTLSKind);
  'initializationStyle'?: (_ctk_ast_v1_DeclVariableInitializationStyle);
  'isStaticDataMember'?: (boolean);
  'initializerFromAnyDeclaration'?: (_ctk_ast_v1_ExpressionValue | null);
  '_tlsKind'?: "tlsKind";
  '_initializationStyle'?: "initializationStyle";
  '_isStaticDataMember'?: "isStaticDataMember";
}

export interface VarDecl__Output {
  'variable': (_ctk_ast_v1_VarDeclInfo__Output | null);
  'tlsKind'?: (_ctk_ast_v1_DeclVariableTLSKind__Output);
  'initializationStyle'?: (_ctk_ast_v1_DeclVariableInitializationStyle__Output);
  'isStaticDataMember'?: (boolean);
  'initializerFromAnyDeclaration': (_ctk_ast_v1_ExpressionValue__Output | null);
  '_tlsKind'?: "tlsKind";
  '_initializationStyle'?: "initializationStyle";
  '_isStaticDataMember'?: "isStaticDataMember";
}
