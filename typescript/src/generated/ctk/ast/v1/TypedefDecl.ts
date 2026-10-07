// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeDeclInfo as _ctk_ast_v1_TypeDeclInfo, TypeDeclInfo__Output as _ctk_ast_v1_TypeDeclInfo__Output } from '../../../ctk/ast/v1/TypeDeclInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';

export interface TypedefDecl {
  'typeDeclaration'?: (_ctk_ast_v1_TypeDeclInfo | null);
  'underlyingType'?: (_ctk_ast_v1_QualType | null);
}

export interface TypedefDecl__Output {
  'typeDeclaration': (_ctk_ast_v1_TypeDeclInfo__Output | null);
  'underlyingType': (_ctk_ast_v1_QualType__Output | null);
}
