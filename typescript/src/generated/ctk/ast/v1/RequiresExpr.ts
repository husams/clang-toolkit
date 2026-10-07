// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { DeclarationValue as _ctk_ast_v1_DeclarationValue, DeclarationValue__Output as _ctk_ast_v1_DeclarationValue__Output } from '../../../ctk/ast/v1/DeclarationValue.js';
import type { ConceptRequirement as _ctk_ast_v1_ConceptRequirement, ConceptRequirement__Output as _ctk_ast_v1_ConceptRequirement__Output } from '../../../ctk/ast/v1/ConceptRequirement.js';

export interface RequiresExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'bodyDeclaration'?: (_ctk_ast_v1_DeclarationValue | null);
  'requirements'?: (_ctk_ast_v1_ConceptRequirement)[];
  'isSatisfied'?: (boolean);
  '_isSatisfied'?: "isSatisfied";
}

export interface RequiresExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'bodyDeclaration': (_ctk_ast_v1_DeclarationValue__Output | null);
  'requirements': (_ctk_ast_v1_ConceptRequirement__Output)[];
  'isSatisfied'?: (boolean);
  '_isSatisfied'?: "isSatisfied";
}
