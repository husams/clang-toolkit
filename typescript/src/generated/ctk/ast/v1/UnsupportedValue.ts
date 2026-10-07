// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/node.proto

import type { UnsupportedReason as _ctk_ast_v1_UnsupportedReason, UnsupportedReason__Output as _ctk_ast_v1_UnsupportedReason__Output } from '../../../ctk/ast/v1/UnsupportedReason.js';

export interface UnsupportedValue {
  'clangKind'?: (string);
  'clangClass'?: (string);
  'reason'?: (_ctk_ast_v1_UnsupportedReason);
  'detail'?: (string);
  '_clangKind'?: "clangKind";
  '_clangClass'?: "clangClass";
  '_reason'?: "reason";
  '_detail'?: "detail";
}

export interface UnsupportedValue__Output {
  'clangKind'?: (string);
  'clangClass'?: (string);
  'reason'?: (_ctk_ast_v1_UnsupportedReason__Output);
  'detail'?: (string);
  '_clangKind'?: "clangKind";
  '_clangClass'?: "clangClass";
  '_reason'?: "reason";
  '_detail'?: "detail";
}
