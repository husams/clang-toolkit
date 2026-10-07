// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TemplateArgumentDescriptionKind as _ctk_ast_v1_TemplateArgumentDescriptionKind, TemplateArgumentDescriptionKind__Output as _ctk_ast_v1_TemplateArgumentDescriptionKind__Output } from '../../../ctk/ast/v1/TemplateArgumentDescriptionKind.js';
import type { TypeDescription as _ctk_ast_v1_TypeDescription, TypeDescription__Output as _ctk_ast_v1_TypeDescription__Output } from '../../../ctk/ast/v1/TypeDescription.js';
import type { APSIntBits as _ctk_ast_v1_APSIntBits, APSIntBits__Output as _ctk_ast_v1_APSIntBits__Output } from '../../../ctk/ast/v1/APSIntBits.js';
import type { APFloatBits as _ctk_ast_v1_APFloatBits, APFloatBits__Output as _ctk_ast_v1_APFloatBits__Output } from '../../../ctk/ast/v1/APFloatBits.js';
import type { TemplateArgumentDescription as _ctk_ast_v1_TemplateArgumentDescription, TemplateArgumentDescription__Output as _ctk_ast_v1_TemplateArgumentDescription__Output } from '../../../ctk/ast/v1/TemplateArgumentDescription.js';

export interface TemplateArgumentDescription {
  'kind'?: (_ctk_ast_v1_TemplateArgumentDescriptionKind);
  'semanticSpelling'?: (string);
  'type'?: (_ctk_ast_v1_TypeDescription | null);
  'integer'?: (_ctk_ast_v1_APSIntBits | null);
  'floating'?: (_ctk_ast_v1_APFloatBits | null);
  'packElements'?: (_ctk_ast_v1_TemplateArgumentDescription)[];
  '_kind'?: "kind";
  '_semanticSpelling'?: "semanticSpelling";
}

export interface TemplateArgumentDescription__Output {
  'kind'?: (_ctk_ast_v1_TemplateArgumentDescriptionKind__Output);
  'semanticSpelling'?: (string);
  'type': (_ctk_ast_v1_TypeDescription__Output | null);
  'integer': (_ctk_ast_v1_APSIntBits__Output | null);
  'floating': (_ctk_ast_v1_APFloatBits__Output | null);
  'packElements': (_ctk_ast_v1_TemplateArgumentDescription__Output)[];
  '_kind'?: "kind";
  '_semanticSpelling'?: "semanticSpelling";
}
