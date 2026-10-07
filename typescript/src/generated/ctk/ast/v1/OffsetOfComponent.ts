// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { CXXBaseSpecifier as _ctk_ast_v1_CXXBaseSpecifier, CXXBaseSpecifier__Output as _ctk_ast_v1_CXXBaseSpecifier__Output } from '../../../ctk/ast/v1/CXXBaseSpecifier.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { Long } from '@grpc/proto-loader';

export interface OffsetOfComponent {
  'field'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'arrayIndex'?: (number | string | Long);
  'identifier'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'base'?: (_ctk_ast_v1_CXXBaseSpecifier | null);
  'identifierName'?: (string);
  'indexExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'kind'?: "field"|"arrayIndex"|"identifier"|"base"|"identifierName"|"indexExpression";
}

export interface OffsetOfComponent__Output {
  'field'?: (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'arrayIndex'?: (string);
  'identifier'?: (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'base'?: (_ctk_ast_v1_CXXBaseSpecifier__Output | null);
  'identifierName'?: (string);
  'indexExpression'?: (_ctk_ast_v1_ExpressionValue__Output | null);
  'kind'?: "field"|"arrayIndex"|"identifier"|"base"|"identifierName"|"indexExpression";
}
