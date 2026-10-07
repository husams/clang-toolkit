// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';

export interface SubstTemplateTypeParmType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'replacementType'?: (_ctk_ast_v1_QualType | null);
  'associatedDeclaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'replacedParameter'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'parameterIndex'?: (number);
  'packIndex'?: (number);
  'isFinal'?: (boolean);
  '_parameterIndex'?: "parameterIndex";
  '_packIndex'?: "packIndex";
  '_isFinal'?: "isFinal";
}

export interface SubstTemplateTypeParmType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'replacementType': (_ctk_ast_v1_QualType__Output | null);
  'associatedDeclaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'replacedParameter': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'parameterIndex'?: (number);
  'packIndex'?: (number);
  'isFinal'?: (boolean);
  '_parameterIndex'?: "parameterIndex";
  '_packIndex'?: "packIndex";
  '_isFinal'?: "isFinal";
}
