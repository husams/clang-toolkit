// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { TemplateName as _ctk_ast_v1_TemplateName, TemplateName__Output as _ctk_ast_v1_TemplateName__Output } from '../../../ctk/ast/v1/TemplateName.js';

export interface SubstitutedTemplateName {
  'parameter'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'replacement'?: (_ctk_ast_v1_TemplateName | null);
  'parameterIndex'?: (number);
  'packIndex'?: (number);
  'isFinal'?: (boolean);
  '_parameterIndex'?: "parameterIndex";
  '_packIndex'?: "packIndex";
  '_isFinal'?: "isFinal";
}

export interface SubstitutedTemplateName__Output {
  'parameter': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'replacement': (_ctk_ast_v1_TemplateName__Output | null);
  'parameterIndex'?: (number);
  'packIndex'?: (number);
  'isFinal'?: (boolean);
  '_parameterIndex'?: "parameterIndex";
  '_packIndex'?: "packIndex";
  '_isFinal'?: "isFinal";
}
