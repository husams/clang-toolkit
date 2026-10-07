// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { APValue as _ctk_ast_v1_APValue, APValue__Output as _ctk_ast_v1_APValue__Output } from '../../../ctk/ast/v1/APValue.js';

export interface APUnionValue {
  'activeField'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'value'?: (_ctk_ast_v1_APValue | null);
}

export interface APUnionValue__Output {
  'activeField': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'value': (_ctk_ast_v1_APValue__Output | null);
}
