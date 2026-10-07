// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { Long } from '@grpc/proto-loader';

export interface APLValuePathEntry {
  'arrayIndex'?: (number | string | Long);
  'declaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'isVirtualBase'?: (boolean);
  '_isVirtualBase'?: "isVirtualBase";
  'value'?: "arrayIndex"|"declaration";
}

export interface APLValuePathEntry__Output {
  'arrayIndex'?: (string);
  'declaration'?: (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'isVirtualBase'?: (boolean);
  '_isVirtualBase'?: "isVirtualBase";
  'value'?: "arrayIndex"|"declaration";
}
