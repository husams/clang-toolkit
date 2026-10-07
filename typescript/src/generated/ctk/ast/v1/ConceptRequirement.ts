// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeRequirement as _ctk_ast_v1_TypeRequirement, TypeRequirement__Output as _ctk_ast_v1_TypeRequirement__Output } from '../../../ctk/ast/v1/TypeRequirement.js';
import type { ExprRequirement as _ctk_ast_v1_ExprRequirement, ExprRequirement__Output as _ctk_ast_v1_ExprRequirement__Output } from '../../../ctk/ast/v1/ExprRequirement.js';
import type { NestedRequirement as _ctk_ast_v1_NestedRequirement, NestedRequirement__Output as _ctk_ast_v1_NestedRequirement__Output } from '../../../ctk/ast/v1/NestedRequirement.js';

export interface ConceptRequirement {
  'type'?: (_ctk_ast_v1_TypeRequirement | null);
  'expression'?: (_ctk_ast_v1_ExprRequirement | null);
  'nested'?: (_ctk_ast_v1_NestedRequirement | null);
  'value'?: "type"|"expression"|"nested";
}

export interface ConceptRequirement__Output {
  'type'?: (_ctk_ast_v1_TypeRequirement__Output | null);
  'expression'?: (_ctk_ast_v1_ExprRequirement__Output | null);
  'nested'?: (_ctk_ast_v1_NestedRequirement__Output | null);
  'value'?: "type"|"expression"|"nested";
}
