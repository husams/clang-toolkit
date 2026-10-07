// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { TemplateArgument as _ctk_ast_v1_TemplateArgument, TemplateArgument__Output as _ctk_ast_v1_TemplateArgument__Output } from '../../../ctk/ast/v1/TemplateArgument.js';

export interface SubstNonTypeTemplateParmPackExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'parameterPack'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'arguments'?: (_ctk_ast_v1_ExpressionValue)[];
  'templateArguments'?: (_ctk_ast_v1_TemplateArgument)[];
}

export interface SubstNonTypeTemplateParmPackExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'parameterPack': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'arguments': (_ctk_ast_v1_ExpressionValue__Output)[];
  'templateArguments': (_ctk_ast_v1_TemplateArgument__Output)[];
}
