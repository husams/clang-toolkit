// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';

export interface TemplateTypeParmType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'depth'?: (number);
  'index'?: (number);
  'isPack'?: (boolean);
  'declaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'identifier'?: (string);
  '_depth'?: "depth";
  '_index'?: "index";
  '_isPack'?: "isPack";
  '_identifier'?: "identifier";
}

export interface TemplateTypeParmType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'depth'?: (number);
  'index'?: (number);
  'isPack'?: (boolean);
  'declaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'identifier'?: (string);
  '_depth'?: "depth";
  '_index'?: "index";
  '_isPack'?: "isPack";
  '_identifier'?: "identifier";
}
