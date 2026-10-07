// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { NamedDeclInfo as _ctk_ast_v1_NamedDeclInfo, NamedDeclInfo__Output as _ctk_ast_v1_NamedDeclInfo__Output } from '../../../ctk/ast/v1/NamedDeclInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';

export interface ValueDeclInfo {
  'named'?: (_ctk_ast_v1_NamedDeclInfo | null);
  'type'?: (_ctk_ast_v1_QualType | null);
}

export interface ValueDeclInfo__Output {
  'named': (_ctk_ast_v1_NamedDeclInfo__Output | null);
  'type': (_ctk_ast_v1_QualType__Output | null);
}
