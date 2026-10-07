// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { AccessSpecifier as _ctk_ast_v1_AccessSpecifier, AccessSpecifier__Output as _ctk_ast_v1_AccessSpecifier__Output } from '../../../ctk/ast/v1/AccessSpecifier.js';

export interface CXXBaseSpecifier {
  'type'?: (_ctk_ast_v1_QualType | null);
  'access'?: (_ctk_ast_v1_AccessSpecifier);
  'isVirtual'?: (boolean);
  'isPackExpansion'?: (boolean);
  '_access'?: "access";
  '_isVirtual'?: "isVirtual";
  '_isPackExpansion'?: "isPackExpansion";
}

export interface CXXBaseSpecifier__Output {
  'type': (_ctk_ast_v1_QualType__Output | null);
  'access'?: (_ctk_ast_v1_AccessSpecifier__Output);
  'isVirtual'?: (boolean);
  'isPackExpansion'?: (boolean);
  '_access'?: "access";
  '_isVirtual'?: "isVirtual";
  '_isPackExpansion'?: "isPackExpansion";
}
