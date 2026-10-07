// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { CXXMethodDeclInfo as _ctk_ast_v1_CXXMethodDeclInfo, CXXMethodDeclInfo__Output as _ctk_ast_v1_CXXMethodDeclInfo__Output } from '../../../ctk/ast/v1/CXXMethodDeclInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface CXXConversionDecl {
  'method'?: (_ctk_ast_v1_CXXMethodDeclInfo | null);
  'isExplicit'?: (boolean);
  'isExplicitSpecifierValue'?: (boolean);
  'explicitSpecifierExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  '_isExplicit'?: "isExplicit";
  '_isExplicitSpecifierValue'?: "isExplicitSpecifierValue";
}

export interface CXXConversionDecl__Output {
  'method': (_ctk_ast_v1_CXXMethodDeclInfo__Output | null);
  'isExplicit'?: (boolean);
  'isExplicitSpecifierValue'?: (boolean);
  'explicitSpecifierExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  '_isExplicit'?: "isExplicit";
  '_isExplicitSpecifierValue'?: "isExplicitSpecifierValue";
}
