// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclarationValue as _ctk_ast_v1_DeclarationValue, DeclarationValue__Output as _ctk_ast_v1_DeclarationValue__Output } from '../../../ctk/ast/v1/DeclarationValue.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface TemplateParameterList {
  'parameters'?: (_ctk_ast_v1_DeclarationValue)[];
  'requiresClause'?: (_ctk_ast_v1_ExpressionValue | null);
}

export interface TemplateParameterList__Output {
  'parameters': (_ctk_ast_v1_DeclarationValue__Output)[];
  'requiresClause': (_ctk_ast_v1_ExpressionValue__Output | null);
}
