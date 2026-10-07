// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/node.proto

import type { AstNode as _ctk_ast_v1_AstNode, AstNode__Output as _ctk_ast_v1_AstNode__Output } from '../../../ctk/ast/v1/AstNode.js';
import type { FieldAvailability as _ctk_ast_v1_FieldAvailability, FieldAvailability__Output as _ctk_ast_v1_FieldAvailability__Output } from '../../../ctk/ast/v1/FieldAvailability.js';
import type { UnsupportedValue as _ctk_ast_v1_UnsupportedValue, UnsupportedValue__Output as _ctk_ast_v1_UnsupportedValue__Output } from '../../../ctk/ast/v1/UnsupportedValue.js';

export interface SemanticResult {
  'values'?: (_ctk_ast_v1_AstNode)[];
  'availability'?: (_ctk_ast_v1_FieldAvailability)[];
  'unsupportedValues'?: (_ctk_ast_v1_UnsupportedValue)[];
  'isComplete'?: (boolean);
  '_isComplete'?: "isComplete";
}

export interface SemanticResult__Output {
  'values': (_ctk_ast_v1_AstNode__Output)[];
  'availability': (_ctk_ast_v1_FieldAvailability__Output)[];
  'unsupportedValues': (_ctk_ast_v1_UnsupportedValue__Output)[];
  'isComplete'?: (boolean);
  '_isComplete'?: "isComplete";
}
