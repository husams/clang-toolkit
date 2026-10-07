// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/cfg_construction_context.proto

import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';
import type { CXXCtorInitializer as _ctk_ast_v1_CXXCtorInitializer, CXXCtorInitializer__Output as _ctk_ast_v1_CXXCtorInitializer__Output } from '../../../ctk/ast/v1/CXXCtorInitializer.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { CfgConstructionContext as _ctk_analysis_v1_CfgConstructionContext, CfgConstructionContext__Output as _ctk_analysis_v1_CfgConstructionContext__Output } from '../../../ctk/analysis/v1/CfgConstructionContext.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { Long } from '@grpc/proto-loader';

// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/cfg_construction_context.proto

export const _ctk_analysis_v1_CfgConstructionContext_Kind = {
  KIND_UNSPECIFIED: 'KIND_UNSPECIFIED',
  SIMPLE_VARIABLE: 'SIMPLE_VARIABLE',
  CXX17_ELIDED_COPY_VARIABLE: 'CXX17_ELIDED_COPY_VARIABLE',
  SIMPLE_CONSTRUCTOR_INITIALIZER: 'SIMPLE_CONSTRUCTOR_INITIALIZER',
  CXX17_ELIDED_COPY_CONSTRUCTOR_INITIALIZER: 'CXX17_ELIDED_COPY_CONSTRUCTOR_INITIALIZER',
  NEW_ALLOCATED_OBJECT: 'NEW_ALLOCATED_OBJECT',
  SIMPLE_TEMPORARY_OBJECT: 'SIMPLE_TEMPORARY_OBJECT',
  ELIDED_TEMPORARY_OBJECT: 'ELIDED_TEMPORARY_OBJECT',
  SIMPLE_RETURNED_VALUE: 'SIMPLE_RETURNED_VALUE',
  CXX17_ELIDED_COPY_RETURNED_VALUE: 'CXX17_ELIDED_COPY_RETURNED_VALUE',
  ARGUMENT: 'ARGUMENT',
  LAMBDA_CAPTURE: 'LAMBDA_CAPTURE',
} as const;

export type _ctk_analysis_v1_CfgConstructionContext_Kind =
  | 'KIND_UNSPECIFIED'
  | 0
  | 'SIMPLE_VARIABLE'
  | 1
  | 'CXX17_ELIDED_COPY_VARIABLE'
  | 2
  | 'SIMPLE_CONSTRUCTOR_INITIALIZER'
  | 3
  | 'CXX17_ELIDED_COPY_CONSTRUCTOR_INITIALIZER'
  | 4
  | 'NEW_ALLOCATED_OBJECT'
  | 5
  | 'SIMPLE_TEMPORARY_OBJECT'
  | 6
  | 'ELIDED_TEMPORARY_OBJECT'
  | 7
  | 'SIMPLE_RETURNED_VALUE'
  | 8
  | 'CXX17_ELIDED_COPY_RETURNED_VALUE'
  | 9
  | 'ARGUMENT'
  | 10
  | 'LAMBDA_CAPTURE'
  | 11

export type _ctk_analysis_v1_CfgConstructionContext_Kind__Output = typeof _ctk_analysis_v1_CfgConstructionContext_Kind[keyof typeof _ctk_analysis_v1_CfgConstructionContext_Kind]

export interface CfgConstructionContext {
  'kind'?: (_ctk_analysis_v1_CfgConstructionContext_Kind);
  'declStatement'?: (_ctk_ast_v1_StatementValue | null);
  'initializer'?: (_ctk_ast_v1_CXXCtorInitializer | null);
  'allocation'?: (_ctk_ast_v1_ExpressionValue | null);
  'temporaryBinding'?: (_ctk_ast_v1_ExpressionValue | null);
  'materialization'?: (_ctk_ast_v1_ExpressionValue | null);
  'constructorAfterElision'?: (_ctk_ast_v1_ExpressionValue | null);
  'contextAfterElision'?: (_ctk_analysis_v1_CfgConstructionContext | null);
  'returnedValue'?: (_ctk_ast_v1_StatementValue | null);
  'callLikeExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'argumentIndex'?: (number | string | Long);
  'lambdaExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'captureIndex'?: (number | string | Long);
  'captureInitializer'?: (_ctk_ast_v1_ExpressionValue | null);
  'captureField'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'arrayInitializationLoop'?: (_ctk_ast_v1_ExpressionValue | null);
  '_argumentIndex'?: "argumentIndex";
  '_captureIndex'?: "captureIndex";
}

export interface CfgConstructionContext__Output {
  'kind': (_ctk_analysis_v1_CfgConstructionContext_Kind__Output);
  'declStatement': (_ctk_ast_v1_StatementValue__Output | null);
  'initializer': (_ctk_ast_v1_CXXCtorInitializer__Output | null);
  'allocation': (_ctk_ast_v1_ExpressionValue__Output | null);
  'temporaryBinding': (_ctk_ast_v1_ExpressionValue__Output | null);
  'materialization': (_ctk_ast_v1_ExpressionValue__Output | null);
  'constructorAfterElision': (_ctk_ast_v1_ExpressionValue__Output | null);
  'contextAfterElision': (_ctk_analysis_v1_CfgConstructionContext__Output | null);
  'returnedValue': (_ctk_ast_v1_StatementValue__Output | null);
  'callLikeExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'argumentIndex'?: (string);
  'lambdaExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'captureIndex'?: (string);
  'captureInitializer': (_ctk_ast_v1_ExpressionValue__Output | null);
  'captureField': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'arrayInitializationLoop': (_ctk_ast_v1_ExpressionValue__Output | null);
  '_argumentIndex'?: "argumentIndex";
  '_captureIndex'?: "captureIndex";
}
