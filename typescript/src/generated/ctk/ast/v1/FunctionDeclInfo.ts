// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclaratorDeclInfo as _ctk_ast_v1_DeclaratorDeclInfo, DeclaratorDeclInfo__Output as _ctk_ast_v1_DeclaratorDeclInfo__Output } from '../../../ctk/ast/v1/DeclaratorDeclInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { DeclarationValue as _ctk_ast_v1_DeclarationValue, DeclarationValue__Output as _ctk_ast_v1_DeclarationValue__Output } from '../../../ctk/ast/v1/DeclarationValue.js';
import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';
import type { StorageClass as _ctk_ast_v1_StorageClass, StorageClass__Output as _ctk_ast_v1_StorageClass__Output } from '../../../ctk/ast/v1/StorageClass.js';

export interface FunctionDeclInfo {
  'declarator'?: (_ctk_ast_v1_DeclaratorDeclInfo | null);
  'returnType'?: (_ctk_ast_v1_QualType | null);
  'parameters'?: (_ctk_ast_v1_DeclarationValue)[];
  'body'?: (_ctk_ast_v1_StatementValue | null);
  'isThisDeclarationADefinition'?: (boolean);
  'isVariadic'?: (boolean);
  'isConstexpr'?: (boolean);
  'storageClass'?: (_ctk_ast_v1_StorageClass);
  '_isThisDeclarationADefinition'?: "isThisDeclarationADefinition";
  '_isVariadic'?: "isVariadic";
  '_isConstexpr'?: "isConstexpr";
  '_storageClass'?: "storageClass";
}

export interface FunctionDeclInfo__Output {
  'declarator': (_ctk_ast_v1_DeclaratorDeclInfo__Output | null);
  'returnType': (_ctk_ast_v1_QualType__Output | null);
  'parameters': (_ctk_ast_v1_DeclarationValue__Output)[];
  'body': (_ctk_ast_v1_StatementValue__Output | null);
  'isThisDeclarationADefinition'?: (boolean);
  'isVariadic'?: (boolean);
  'isConstexpr'?: (boolean);
  'storageClass'?: (_ctk_ast_v1_StorageClass__Output);
  '_isThisDeclarationADefinition'?: "isThisDeclarationADefinition";
  '_isVariadic'?: "isVariadic";
  '_isConstexpr'?: "isConstexpr";
  '_storageClass'?: "storageClass";
}
