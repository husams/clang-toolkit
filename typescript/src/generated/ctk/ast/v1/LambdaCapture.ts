// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { LambdaCaptureKind as _ctk_ast_v1_LambdaCaptureKind, LambdaCaptureKind__Output as _ctk_ast_v1_LambdaCaptureKind__Output } from '../../../ctk/ast/v1/LambdaCaptureKind.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';

export interface LambdaCapture {
  'kind'?: (_ctk_ast_v1_LambdaCaptureKind);
  'variable'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'isImplicit'?: (boolean);
  'isPackExpansion'?: (boolean);
  '_kind'?: "kind";
  '_isImplicit'?: "isImplicit";
  '_isPackExpansion'?: "isPackExpansion";
}

export interface LambdaCapture__Output {
  'kind'?: (_ctk_ast_v1_LambdaCaptureKind__Output);
  'variable': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'isImplicit'?: (boolean);
  'isPackExpansion'?: (boolean);
  '_kind'?: "kind";
  '_isImplicit'?: "isImplicit";
  '_isPackExpansion'?: "isPackExpansion";
}
