// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ConceptReference as _ctk_ast_v1_ConceptReference, ConceptReference__Output as _ctk_ast_v1_ConceptReference__Output } from '../../../ctk/ast/v1/ConceptReference.js';
import type { TemplateArgument as _ctk_ast_v1_TemplateArgument, TemplateArgument__Output as _ctk_ast_v1_TemplateArgument__Output } from '../../../ctk/ast/v1/TemplateArgument.js';

export interface ConceptSpecializationExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'conceptReference'?: (_ctk_ast_v1_ConceptReference | null);
  'templateArguments'?: (_ctk_ast_v1_TemplateArgument)[];
  'isSatisfied'?: (boolean);
  '_isSatisfied'?: "isSatisfied";
}

export interface ConceptSpecializationExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'conceptReference': (_ctk_ast_v1_ConceptReference__Output | null);
  'templateArguments': (_ctk_ast_v1_TemplateArgument__Output)[];
  'isSatisfied'?: (boolean);
  '_isSatisfied'?: "isSatisfied";
}
