// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface AsmOperand {
  'symbolicName'?: (string);
  'constraint'?: (string);
  'expression'?: (_ctk_ast_v1_ExpressionValue | null);
  '_symbolicName'?: "symbolicName";
  '_constraint'?: "constraint";
}

export interface AsmOperand__Output {
  'symbolicName'?: (string);
  'constraint'?: (string);
  'expression': (_ctk_ast_v1_ExpressionValue__Output | null);
  '_symbolicName'?: "symbolicName";
  '_constraint'?: "constraint";
}
