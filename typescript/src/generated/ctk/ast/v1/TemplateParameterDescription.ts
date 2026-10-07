// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TemplateParameterDescriptionKind as _ctk_ast_v1_TemplateParameterDescriptionKind, TemplateParameterDescriptionKind__Output as _ctk_ast_v1_TemplateParameterDescriptionKind__Output } from '../../../ctk/ast/v1/TemplateParameterDescriptionKind.js';
import type { TypeDescription as _ctk_ast_v1_TypeDescription, TypeDescription__Output as _ctk_ast_v1_TypeDescription__Output } from '../../../ctk/ast/v1/TypeDescription.js';
import type { TemplateParameterDescription as _ctk_ast_v1_TemplateParameterDescription, TemplateParameterDescription__Output as _ctk_ast_v1_TemplateParameterDescription__Output } from '../../../ctk/ast/v1/TemplateParameterDescription.js';

export interface TemplateParameterDescription {
  'kind'?: (_ctk_ast_v1_TemplateParameterDescriptionKind);
  'name'?: (string);
  'type'?: (_ctk_ast_v1_TypeDescription | null);
  'isParameterPack'?: (boolean);
  'templateParameters'?: (_ctk_ast_v1_TemplateParameterDescription)[];
  '_kind'?: "kind";
  '_name'?: "name";
  '_isParameterPack'?: "isParameterPack";
}

export interface TemplateParameterDescription__Output {
  'kind'?: (_ctk_ast_v1_TemplateParameterDescriptionKind__Output);
  'name'?: (string);
  'type': (_ctk_ast_v1_TypeDescription__Output | null);
  'isParameterPack'?: (boolean);
  'templateParameters': (_ctk_ast_v1_TemplateParameterDescription__Output)[];
  '_kind'?: "kind";
  '_name'?: "name";
  '_isParameterPack'?: "isParameterPack";
}
