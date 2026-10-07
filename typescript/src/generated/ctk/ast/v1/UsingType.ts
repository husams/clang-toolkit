// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { NestedNameSpecifier as _ctk_ast_v1_NestedNameSpecifier, NestedNameSpecifier__Output as _ctk_ast_v1_NestedNameSpecifier__Output } from '../../../ctk/ast/v1/NestedNameSpecifier.js';

export interface UsingType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'shadowDeclaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'desugaredType'?: (_ctk_ast_v1_QualType | null);
  'qualifier'?: (_ctk_ast_v1_NestedNameSpecifier | null);
}

export interface UsingType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'shadowDeclaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'desugaredType': (_ctk_ast_v1_QualType__Output | null);
  'qualifier': (_ctk_ast_v1_NestedNameSpecifier__Output | null);
}
