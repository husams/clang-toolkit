// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeValue as _ctk_ast_v1_TypeValue, TypeValue__Output as _ctk_ast_v1_TypeValue__Output } from '../../../ctk/ast/v1/TypeValue.js';
import type { Qualifiers as _ctk_ast_v1_Qualifiers, Qualifiers__Output as _ctk_ast_v1_Qualifiers__Output } from '../../../ctk/ast/v1/Qualifiers.js';
import type { TypeDescription as _ctk_ast_v1_TypeDescription, TypeDescription__Output as _ctk_ast_v1_TypeDescription__Output } from '../../../ctk/ast/v1/TypeDescription.js';

export interface QualType {
  'type'?: (_ctk_ast_v1_TypeValue | null);
  'qualifiers'?: (_ctk_ast_v1_Qualifiers | null);
  'description'?: (_ctk_ast_v1_TypeDescription | null);
}

export interface QualType__Output {
  'type': (_ctk_ast_v1_TypeValue__Output | null);
  'qualifiers': (_ctk_ast_v1_Qualifiers__Output | null);
  'description': (_ctk_ast_v1_TypeDescription__Output | null);
}
