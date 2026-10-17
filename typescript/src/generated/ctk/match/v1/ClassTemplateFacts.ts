// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_result.proto

import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { TemplateParameterDescription as _ctk_ast_v1_TemplateParameterDescription, TemplateParameterDescription__Output as _ctk_ast_v1_TemplateParameterDescription__Output } from '../../../ctk/ast/v1/TemplateParameterDescription.js';
import type { TemplateArgumentDescription as _ctk_ast_v1_TemplateArgumentDescription, TemplateArgumentDescription__Output as _ctk_ast_v1_TemplateArgumentDescription__Output } from '../../../ctk/ast/v1/TemplateArgumentDescription.js';
import type { DeclTemplateSpecializationKind as _ctk_ast_v1_DeclTemplateSpecializationKind, DeclTemplateSpecializationKind__Output as _ctk_ast_v1_DeclTemplateSpecializationKind__Output } from '../../../ctk/ast/v1/DeclTemplateSpecializationKind.js';

// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_result.proto

export const _ctk_match_v1_ClassTemplateFacts_Kind = {
  KIND_UNSPECIFIED: 'KIND_UNSPECIFIED',
  ORDINARY: 'ORDINARY',
  PRIMARY: 'PRIMARY',
  SPECIALIZATION: 'SPECIALIZATION',
  PARTIAL_SPECIALIZATION: 'PARTIAL_SPECIALIZATION',
} as const;

export type _ctk_match_v1_ClassTemplateFacts_Kind =
  | 'KIND_UNSPECIFIED'
  | 0
  | 'ORDINARY'
  | 1
  | 'PRIMARY'
  | 2
  | 'SPECIALIZATION'
  | 3
  | 'PARTIAL_SPECIALIZATION'
  | 4

export type _ctk_match_v1_ClassTemplateFacts_Kind__Output = typeof _ctk_match_v1_ClassTemplateFacts_Kind[keyof typeof _ctk_match_v1_ClassTemplateFacts_Kind]

export interface ClassTemplateFacts {
  'kind'?: (_ctk_match_v1_ClassTemplateFacts_Kind);
  'displayName'?: (string);
  'primaryTemplate'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'parameters'?: (_ctk_ast_v1_TemplateParameterDescription)[];
  'arguments'?: (_ctk_ast_v1_TemplateArgumentDescription)[];
  'specializationKind'?: (_ctk_ast_v1_DeclTemplateSpecializationKind);
  '_kind'?: "kind";
  '_specializationKind'?: "specializationKind";
}

export interface ClassTemplateFacts__Output {
  'kind'?: (_ctk_match_v1_ClassTemplateFacts_Kind__Output);
  'displayName': (string);
  'primaryTemplate': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'parameters': (_ctk_ast_v1_TemplateParameterDescription__Output)[];
  'arguments': (_ctk_ast_v1_TemplateArgumentDescription__Output)[];
  'specializationKind'?: (_ctk_ast_v1_DeclTemplateSpecializationKind__Output);
  '_kind'?: "kind";
  '_specializationKind'?: "specializationKind";
}
