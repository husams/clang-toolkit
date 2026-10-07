// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { AttributeValue as _ctk_ast_v1_AttributeValue, AttributeValue__Output as _ctk_ast_v1_AttributeValue__Output } from '../../../ctk/ast/v1/AttributeValue.js';

export interface DeclInfo {
  'containingScope'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'attributes'?: (_ctk_ast_v1_AttributeValue)[];
  'isImplicit'?: (boolean);
  'isInvalid'?: (boolean);
  '_isImplicit'?: "isImplicit";
  '_isInvalid'?: "isInvalid";
}

export interface DeclInfo__Output {
  'containingScope': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'attributes': (_ctk_ast_v1_AttributeValue__Output)[];
  'isImplicit'?: (boolean);
  'isInvalid'?: (boolean);
  '_isImplicit'?: "isImplicit";
  '_isInvalid'?: "isInvalid";
}
