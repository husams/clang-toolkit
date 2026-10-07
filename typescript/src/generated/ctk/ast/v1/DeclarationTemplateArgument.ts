// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';

export interface DeclarationTemplateArgument {
  'declaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'parameterType'?: (_ctk_ast_v1_QualType | null);
}

export interface DeclarationTemplateArgument__Output {
  'declaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'parameterType': (_ctk_ast_v1_QualType__Output | null);
}
