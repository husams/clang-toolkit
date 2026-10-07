// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclaratorDeclInfo as _ctk_ast_v1_DeclaratorDeclInfo, DeclaratorDeclInfo__Output as _ctk_ast_v1_DeclaratorDeclInfo__Output } from '../../../ctk/ast/v1/DeclaratorDeclInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { StorageClass as _ctk_ast_v1_StorageClass, StorageClass__Output as _ctk_ast_v1_StorageClass__Output } from '../../../ctk/ast/v1/StorageClass.js';

export interface VarDeclInfo {
  'declarator'?: (_ctk_ast_v1_DeclaratorDeclInfo | null);
  'initializer'?: (_ctk_ast_v1_ExpressionValue | null);
  'storageClass'?: (_ctk_ast_v1_StorageClass);
  'isConstexpr'?: (boolean);
  '_storageClass'?: "storageClass";
  '_isConstexpr'?: "isConstexpr";
}

export interface VarDeclInfo__Output {
  'declarator': (_ctk_ast_v1_DeclaratorDeclInfo__Output | null);
  'initializer': (_ctk_ast_v1_ExpressionValue__Output | null);
  'storageClass'?: (_ctk_ast_v1_StorageClass__Output);
  'isConstexpr'?: (boolean);
  '_storageClass'?: "storageClass";
  '_isConstexpr'?: "isConstexpr";
}
