// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { NamedDeclInfo as _ctk_ast_v1_NamedDeclInfo, NamedDeclInfo__Output as _ctk_ast_v1_NamedDeclInfo__Output } from '../../../ctk/ast/v1/NamedDeclInfo.js';
import type { TypeValue as _ctk_ast_v1_TypeValue, TypeValue__Output as _ctk_ast_v1_TypeValue__Output } from '../../../ctk/ast/v1/TypeValue.js';

export interface TypeDeclInfo {
  'named'?: (_ctk_ast_v1_NamedDeclInfo | null);
  'declaredType'?: (_ctk_ast_v1_TypeValue | null);
}

export interface TypeDeclInfo__Output {
  'named': (_ctk_ast_v1_NamedDeclInfo__Output | null);
  'declaredType': (_ctk_ast_v1_TypeValue__Output | null);
}
