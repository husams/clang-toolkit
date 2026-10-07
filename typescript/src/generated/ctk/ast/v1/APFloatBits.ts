// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { FloatingSemantics as _ctk_ast_v1_FloatingSemantics, FloatingSemantics__Output as _ctk_ast_v1_FloatingSemantics__Output } from '../../../ctk/ast/v1/FloatingSemantics.js';
import type { APIntBits as _ctk_ast_v1_APIntBits, APIntBits__Output as _ctk_ast_v1_APIntBits__Output } from '../../../ctk/ast/v1/APIntBits.js';

export interface APFloatBits {
  'semantics'?: (_ctk_ast_v1_FloatingSemantics);
  'bitPattern'?: (_ctk_ast_v1_APIntBits | null);
  'decimalValue'?: (string);
  '_semantics'?: "semantics";
  '_decimalValue'?: "decimalValue";
}

export interface APFloatBits__Output {
  'semantics'?: (_ctk_ast_v1_FloatingSemantics__Output);
  'bitPattern': (_ctk_ast_v1_APIntBits__Output | null);
  'decimalValue'?: (string);
  '_semantics'?: "semantics";
  '_decimalValue'?: "decimalValue";
}
