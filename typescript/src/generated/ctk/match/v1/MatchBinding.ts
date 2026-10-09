// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_result.proto

import type { AstNode as _ctk_ast_v1_AstNode, AstNode__Output as _ctk_ast_v1_AstNode__Output } from '../../../ctk/ast/v1/AstNode.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { UnsupportedValue as _ctk_ast_v1_UnsupportedValue, UnsupportedValue__Output as _ctk_ast_v1_UnsupportedValue__Output } from '../../../ctk/ast/v1/UnsupportedValue.js';
import type { FieldAvailability as _ctk_ast_v1_FieldAvailability, FieldAvailability__Output as _ctk_ast_v1_FieldAvailability__Output } from '../../../ctk/ast/v1/FieldAvailability.js';
import type { BindingMatchScope as _ctk_match_v1_BindingMatchScope, BindingMatchScope__Output as _ctk_match_v1_BindingMatchScope__Output } from '../../../ctk/match/v1/BindingMatchScope.js';
import type { MatchSourcePoint as _ctk_match_v1_MatchSourcePoint, MatchSourcePoint__Output as _ctk_match_v1_MatchSourcePoint__Output } from '../../../ctk/match/v1/MatchSourcePoint.js';
import type { MatchSourceRange as _ctk_match_v1_MatchSourceRange, MatchSourceRange__Output as _ctk_match_v1_MatchSourceRange__Output } from '../../../ctk/match/v1/MatchSourceRange.js';
import type { CallSiteFacts as _ctk_match_v1_CallSiteFacts, CallSiteFacts__Output as _ctk_match_v1_CallSiteFacts__Output } from '../../../ctk/match/v1/CallSiteFacts.js';
import type { CXXBaseSpecifier as _ctk_ast_v1_CXXBaseSpecifier, CXXBaseSpecifier__Output as _ctk_ast_v1_CXXBaseSpecifier__Output } from '../../../ctk/ast/v1/CXXBaseSpecifier.js';

export interface MatchBinding {
  'node'?: (_ctk_ast_v1_AstNode | null);
  'qualifiedType'?: (_ctk_ast_v1_QualType | null);
  'unsupported'?: (_ctk_ast_v1_UnsupportedValue | null);
  'availability'?: (_ctk_ast_v1_FieldAvailability)[];
  'isComplete'?: (boolean);
  'supportedScopes'?: (_ctk_match_v1_BindingMatchScope)[];
  'location'?: (_ctk_match_v1_MatchSourcePoint | null);
  'range'?: (_ctk_match_v1_MatchSourceRange | null);
  'symbolIdentity'?: (string);
  'documentation'?: (string);
  'callSite'?: (_ctk_match_v1_CallSiteFacts | null);
  'baseSpecifier'?: (_ctk_ast_v1_CXXBaseSpecifier | null);
  'value'?: "node"|"qualifiedType"|"unsupported"|"baseSpecifier";
  '_isComplete'?: "isComplete";
}

export interface MatchBinding__Output {
  'node'?: (_ctk_ast_v1_AstNode__Output | null);
  'qualifiedType'?: (_ctk_ast_v1_QualType__Output | null);
  'unsupported'?: (_ctk_ast_v1_UnsupportedValue__Output | null);
  'availability': (_ctk_ast_v1_FieldAvailability__Output)[];
  'isComplete'?: (boolean);
  'supportedScopes': (_ctk_match_v1_BindingMatchScope__Output)[];
  'location': (_ctk_match_v1_MatchSourcePoint__Output | null);
  'range': (_ctk_match_v1_MatchSourceRange__Output | null);
  'symbolIdentity': (string);
  'documentation': (string);
  'callSite': (_ctk_match_v1_CallSiteFacts__Output | null);
  'baseSpecifier'?: (_ctk_ast_v1_CXXBaseSpecifier__Output | null);
  'value'?: "node"|"qualifiedType"|"unsupported"|"baseSpecifier";
  '_isComplete'?: "isComplete";
}
