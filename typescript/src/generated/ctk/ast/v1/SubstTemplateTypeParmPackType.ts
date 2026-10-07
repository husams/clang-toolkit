// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { TemplateArgument as _ctk_ast_v1_TemplateArgument, TemplateArgument__Output as _ctk_ast_v1_TemplateArgument__Output } from '../../../ctk/ast/v1/TemplateArgument.js';

export interface SubstTemplateTypeParmPackType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'associatedDeclaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'replacedParameter'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'parameterIndex'?: (number);
  'isFinal'?: (boolean);
  'argumentPack'?: (_ctk_ast_v1_TemplateArgument | null);
  '_parameterIndex'?: "parameterIndex";
  '_isFinal'?: "isFinal";
}

export interface SubstTemplateTypeParmPackType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'associatedDeclaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'replacedParameter': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'parameterIndex'?: (number);
  'isFinal'?: (boolean);
  'argumentPack': (_ctk_ast_v1_TemplateArgument__Output | null);
  '_parameterIndex'?: "parameterIndex";
  '_isFinal'?: "isFinal";
}
