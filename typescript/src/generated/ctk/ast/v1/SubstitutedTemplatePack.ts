// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { TemplateArgument as _ctk_ast_v1_TemplateArgument, TemplateArgument__Output as _ctk_ast_v1_TemplateArgument__Output } from '../../../ctk/ast/v1/TemplateArgument.js';

export interface SubstitutedTemplatePack {
  'parameter'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'arguments'?: (_ctk_ast_v1_TemplateArgument)[];
  'parameterIndex'?: (number);
  'isFinal'?: (boolean);
  '_parameterIndex'?: "parameterIndex";
  '_isFinal'?: "isFinal";
}

export interface SubstitutedTemplatePack__Output {
  'parameter': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'arguments': (_ctk_ast_v1_TemplateArgument__Output)[];
  'parameterIndex'?: (number);
  'isFinal'?: (boolean);
  '_parameterIndex'?: "parameterIndex";
  '_isFinal'?: "isFinal";
}
