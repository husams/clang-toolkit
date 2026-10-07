// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_result.proto

import type { AstNode as _ctk_ast_v1_AstNode, AstNode__Output as _ctk_ast_v1_AstNode__Output } from '../../../ctk/ast/v1/AstNode.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { UnsupportedValue as _ctk_ast_v1_UnsupportedValue, UnsupportedValue__Output as _ctk_ast_v1_UnsupportedValue__Output } from '../../../ctk/ast/v1/UnsupportedValue.js';
import type { FieldAvailability as _ctk_ast_v1_FieldAvailability, FieldAvailability__Output as _ctk_ast_v1_FieldAvailability__Output } from '../../../ctk/ast/v1/FieldAvailability.js';
import type { BindingMatchScope as _ctk_match_v1_BindingMatchScope, BindingMatchScope__Output as _ctk_match_v1_BindingMatchScope__Output } from '../../../ctk/match/v1/BindingMatchScope.js';

export interface MatchBinding {
  'node'?: (_ctk_ast_v1_AstNode | null);
  'qualifiedType'?: (_ctk_ast_v1_QualType | null);
  'unsupported'?: (_ctk_ast_v1_UnsupportedValue | null);
  'availability'?: (_ctk_ast_v1_FieldAvailability)[];
  'isComplete'?: (boolean);
  'supportedScopes'?: (_ctk_match_v1_BindingMatchScope)[];
  'value'?: "node"|"qualifiedType"|"unsupported";
  '_isComplete'?: "isComplete";
}

export interface MatchBinding__Output {
  'node'?: (_ctk_ast_v1_AstNode__Output | null);
  'qualifiedType'?: (_ctk_ast_v1_QualType__Output | null);
  'unsupported'?: (_ctk_ast_v1_UnsupportedValue__Output | null);
  'availability': (_ctk_ast_v1_FieldAvailability__Output)[];
  'isComplete'?: (boolean);
  'supportedScopes': (_ctk_match_v1_BindingMatchScope__Output)[];
  'value'?: "node"|"qualifiedType"|"unsupported";
  '_isComplete'?: "isComplete";
}
