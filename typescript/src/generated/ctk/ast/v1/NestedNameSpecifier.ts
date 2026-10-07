// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { Empty as _ctk_ast_v1_Empty, Empty__Output as _ctk_ast_v1_Empty__Output } from '../../../ctk/ast/v1/Empty.js';
import type { NestedNamespaceName as _ctk_ast_v1_NestedNamespaceName, NestedNamespaceName__Output as _ctk_ast_v1_NestedNamespaceName__Output } from '../../../ctk/ast/v1/NestedNamespaceName.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';

export interface NestedNameSpecifier {
  'nullSpecifier'?: (_ctk_ast_v1_Empty | null);
  'global'?: (_ctk_ast_v1_Empty | null);
  'namespaceName'?: (_ctk_ast_v1_NestedNamespaceName | null);
  'type'?: (_ctk_ast_v1_QualType | null);
  'microsoftSuperRecord'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'value'?: "nullSpecifier"|"global"|"namespaceName"|"type"|"microsoftSuperRecord";
}

export interface NestedNameSpecifier__Output {
  'nullSpecifier'?: (_ctk_ast_v1_Empty__Output | null);
  'global'?: (_ctk_ast_v1_Empty__Output | null);
  'namespaceName'?: (_ctk_ast_v1_NestedNamespaceName__Output | null);
  'type'?: (_ctk_ast_v1_QualType__Output | null);
  'microsoftSuperRecord'?: (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'value'?: "nullSpecifier"|"global"|"namespaceName"|"type"|"microsoftSuperRecord";
}
