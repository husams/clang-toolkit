// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface BlockCaptureInfo {
  'variable'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'isByRef'?: (boolean);
  'isNested'?: (boolean);
  'copyExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  '_isByRef'?: "isByRef";
  '_isNested'?: "isNested";
}

export interface BlockCaptureInfo__Output {
  'variable': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'isByRef'?: (boolean);
  'isNested'?: (boolean);
  'copyExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  '_isByRef'?: "isByRef";
  '_isNested'?: "isNested";
}
