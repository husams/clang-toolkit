// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeDescription as _ctk_ast_v1_TypeDescription, TypeDescription__Output as _ctk_ast_v1_TypeDescription__Output } from '../../../ctk/ast/v1/TypeDescription.js';

export interface ParameterValue {
  'name'?: (string);
  'type'?: (_ctk_ast_v1_TypeDescription | null);
  'isParameterPack'?: (boolean);
  '_name'?: "name";
  '_isParameterPack'?: "isParameterPack";
}

export interface ParameterValue__Output {
  'name'?: (string);
  'type': (_ctk_ast_v1_TypeDescription__Output | null);
  'isParameterPack'?: (boolean);
  '_name'?: "name";
  '_isParameterPack'?: "isParameterPack";
}
