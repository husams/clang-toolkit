// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/cfg_element.proto

import type { CfgStatement as _ctk_analysis_v1_CfgStatement, CfgStatement__Output as _ctk_analysis_v1_CfgStatement__Output } from '../../../ctk/analysis/v1/CfgStatement.js';
import type { CfgInitializer as _ctk_analysis_v1_CfgInitializer, CfgInitializer__Output as _ctk_analysis_v1_CfgInitializer__Output } from '../../../ctk/analysis/v1/CfgInitializer.js';
import type { CfgScopeEvent as _ctk_analysis_v1_CfgScopeEvent, CfgScopeEvent__Output as _ctk_analysis_v1_CfgScopeEvent__Output } from '../../../ctk/analysis/v1/CfgScopeEvent.js';
import type { CfgNewAllocator as _ctk_analysis_v1_CfgNewAllocator, CfgNewAllocator__Output as _ctk_analysis_v1_CfgNewAllocator__Output } from '../../../ctk/analysis/v1/CfgNewAllocator.js';
import type { CfgLoopExit as _ctk_analysis_v1_CfgLoopExit, CfgLoopExit__Output as _ctk_analysis_v1_CfgLoopExit__Output } from '../../../ctk/analysis/v1/CfgLoopExit.js';
import type { CfgDestructor as _ctk_analysis_v1_CfgDestructor, CfgDestructor__Output as _ctk_analysis_v1_CfgDestructor__Output } from '../../../ctk/analysis/v1/CfgDestructor.js';
import type { CfgCleanup as _ctk_analysis_v1_CfgCleanup, CfgCleanup__Output as _ctk_analysis_v1_CfgCleanup__Output } from '../../../ctk/analysis/v1/CfgCleanup.js';
import type { FieldAvailability as _ctk_ast_v1_FieldAvailability, FieldAvailability__Output as _ctk_ast_v1_FieldAvailability__Output } from '../../../ctk/ast/v1/FieldAvailability.js';

// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/cfg_element.proto

export const _ctk_analysis_v1_CfgElement_Kind = {
  KIND_UNSPECIFIED: 'KIND_UNSPECIFIED',
  INITIALIZER: 'INITIALIZER',
  SCOPE_BEGIN: 'SCOPE_BEGIN',
  SCOPE_END: 'SCOPE_END',
  NEW_ALLOCATOR: 'NEW_ALLOCATOR',
  LIFETIME_ENDS: 'LIFETIME_ENDS',
  LOOP_EXIT: 'LOOP_EXIT',
  STATEMENT: 'STATEMENT',
  CONSTRUCTOR: 'CONSTRUCTOR',
  CXX_RECORD_TYPED_CALL: 'CXX_RECORD_TYPED_CALL',
  AUTOMATIC_OBJECT_DTOR: 'AUTOMATIC_OBJECT_DTOR',
  DELETE_DTOR: 'DELETE_DTOR',
  BASE_DTOR: 'BASE_DTOR',
  MEMBER_DTOR: 'MEMBER_DTOR',
  TEMPORARY_DTOR: 'TEMPORARY_DTOR',
  CLEANUP_FUNCTION: 'CLEANUP_FUNCTION',
} as const;

export type _ctk_analysis_v1_CfgElement_Kind =
  | 'KIND_UNSPECIFIED'
  | 0
  | 'INITIALIZER'
  | 1
  | 'SCOPE_BEGIN'
  | 2
  | 'SCOPE_END'
  | 3
  | 'NEW_ALLOCATOR'
  | 4
  | 'LIFETIME_ENDS'
  | 5
  | 'LOOP_EXIT'
  | 6
  | 'STATEMENT'
  | 7
  | 'CONSTRUCTOR'
  | 8
  | 'CXX_RECORD_TYPED_CALL'
  | 9
  | 'AUTOMATIC_OBJECT_DTOR'
  | 10
  | 'DELETE_DTOR'
  | 11
  | 'BASE_DTOR'
  | 12
  | 'MEMBER_DTOR'
  | 13
  | 'TEMPORARY_DTOR'
  | 14
  | 'CLEANUP_FUNCTION'
  | 15

export type _ctk_analysis_v1_CfgElement_Kind__Output = typeof _ctk_analysis_v1_CfgElement_Kind[keyof typeof _ctk_analysis_v1_CfgElement_Kind]

export interface CfgElement {
  'kind'?: (_ctk_analysis_v1_CfgElement_Kind);
  'statement'?: (_ctk_analysis_v1_CfgStatement | null);
  'initializer'?: (_ctk_analysis_v1_CfgInitializer | null);
  'scope'?: (_ctk_analysis_v1_CfgScopeEvent | null);
  'allocator'?: (_ctk_analysis_v1_CfgNewAllocator | null);
  'loopExit'?: (_ctk_analysis_v1_CfgLoopExit | null);
  'destructor'?: (_ctk_analysis_v1_CfgDestructor | null);
  'cleanup'?: (_ctk_analysis_v1_CfgCleanup | null);
  'isComplete'?: (boolean);
  'availability'?: (_ctk_ast_v1_FieldAvailability)[];
  'value'?: "statement"|"initializer"|"scope"|"allocator"|"loopExit"|"destructor"|"cleanup";
  '_isComplete'?: "isComplete";
}

export interface CfgElement__Output {
  'kind': (_ctk_analysis_v1_CfgElement_Kind__Output);
  'statement'?: (_ctk_analysis_v1_CfgStatement__Output | null);
  'initializer'?: (_ctk_analysis_v1_CfgInitializer__Output | null);
  'scope'?: (_ctk_analysis_v1_CfgScopeEvent__Output | null);
  'allocator'?: (_ctk_analysis_v1_CfgNewAllocator__Output | null);
  'loopExit'?: (_ctk_analysis_v1_CfgLoopExit__Output | null);
  'destructor'?: (_ctk_analysis_v1_CfgDestructor__Output | null);
  'cleanup'?: (_ctk_analysis_v1_CfgCleanup__Output | null);
  'isComplete'?: (boolean);
  'availability': (_ctk_ast_v1_FieldAvailability__Output)[];
  'value'?: "statement"|"initializer"|"scope"|"allocator"|"loopExit"|"destructor"|"cleanup";
  '_isComplete'?: "isComplete";
}
