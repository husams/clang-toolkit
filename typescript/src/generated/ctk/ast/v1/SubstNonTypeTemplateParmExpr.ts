// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface SubstNonTypeTemplateParmExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'parameter'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'replacement'?: (_ctk_ast_v1_ExpressionValue | null);
  'parameterIndex'?: (number);
  '_parameterIndex'?: "parameterIndex";
}

export interface SubstNonTypeTemplateParmExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'parameter': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'replacement': (_ctk_ast_v1_ExpressionValue__Output | null);
  'parameterIndex'?: (number);
  '_parameterIndex'?: "parameterIndex";
}
