// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/cfg_block.proto

import type { CfgElement as _ctk_analysis_v1_CfgElement, CfgElement__Output as _ctk_analysis_v1_CfgElement__Output } from '../../../ctk/analysis/v1/CfgElement.js';
import type { CfgEdge as _ctk_analysis_v1_CfgEdge, CfgEdge__Output as _ctk_analysis_v1_CfgEdge__Output } from '../../../ctk/analysis/v1/CfgEdge.js';
import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { FieldAvailability as _ctk_ast_v1_FieldAvailability, FieldAvailability__Output as _ctk_ast_v1_FieldAvailability__Output } from '../../../ctk/ast/v1/FieldAvailability.js';
import type { Long } from '@grpc/proto-loader';

// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/cfg_block.proto

export const _ctk_analysis_v1_CfgBlock_TerminatorKind = {
  TERMINATOR_UNSPECIFIED: 'TERMINATOR_UNSPECIFIED',
  STATEMENT_BRANCH: 'STATEMENT_BRANCH',
  TEMPORARY_DTORS_BRANCH: 'TEMPORARY_DTORS_BRANCH',
  VIRTUAL_BASE_BRANCH: 'VIRTUAL_BASE_BRANCH',
} as const;

export type _ctk_analysis_v1_CfgBlock_TerminatorKind =
  | 'TERMINATOR_UNSPECIFIED'
  | 0
  | 'STATEMENT_BRANCH'
  | 1
  | 'TEMPORARY_DTORS_BRANCH'
  | 2
  | 'VIRTUAL_BASE_BRANCH'
  | 3

export type _ctk_analysis_v1_CfgBlock_TerminatorKind__Output = typeof _ctk_analysis_v1_CfgBlock_TerminatorKind[keyof typeof _ctk_analysis_v1_CfgBlock_TerminatorKind]

export interface CfgBlock {
  'blockIndex'?: (number | string | Long);
  'elements'?: (_ctk_analysis_v1_CfgElement)[];
  'predecessors'?: (_ctk_analysis_v1_CfgEdge)[];
  'successors'?: (_ctk_analysis_v1_CfgEdge)[];
  'label'?: (_ctk_ast_v1_StatementValue | null);
  'loopTarget'?: (_ctk_ast_v1_StatementValue | null);
  'terminatorKind'?: (_ctk_analysis_v1_CfgBlock_TerminatorKind);
  'terminator'?: (_ctk_ast_v1_StatementValue | null);
  'terminatorCondition'?: (_ctk_ast_v1_StatementValue | null);
  'lastCondition'?: (_ctk_ast_v1_ExpressionValue | null);
  'hasNoReturnElement'?: (boolean);
  'isComplete'?: (boolean);
  'availability'?: (_ctk_ast_v1_FieldAvailability)[];
  '_terminatorKind'?: "terminatorKind";
  '_isComplete'?: "isComplete";
}

export interface CfgBlock__Output {
  'blockIndex': (string);
  'elements': (_ctk_analysis_v1_CfgElement__Output)[];
  'predecessors': (_ctk_analysis_v1_CfgEdge__Output)[];
  'successors': (_ctk_analysis_v1_CfgEdge__Output)[];
  'label': (_ctk_ast_v1_StatementValue__Output | null);
  'loopTarget': (_ctk_ast_v1_StatementValue__Output | null);
  'terminatorKind'?: (_ctk_analysis_v1_CfgBlock_TerminatorKind__Output);
  'terminator': (_ctk_ast_v1_StatementValue__Output | null);
  'terminatorCondition': (_ctk_ast_v1_StatementValue__Output | null);
  'lastCondition': (_ctk_ast_v1_ExpressionValue__Output | null);
  'hasNoReturnElement': (boolean);
  'isComplete'?: (boolean);
  'availability': (_ctk_ast_v1_FieldAvailability__Output)[];
  '_terminatorKind'?: "terminatorKind";
  '_isComplete'?: "isComplete";
}
