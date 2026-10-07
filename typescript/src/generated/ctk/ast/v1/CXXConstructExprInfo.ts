// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { ConstructionKind as _ctk_ast_v1_ConstructionKind, ConstructionKind__Output as _ctk_ast_v1_ConstructionKind__Output } from '../../../ctk/ast/v1/ConstructionKind.js';

export interface CXXConstructExprInfo {
  'expression'?: (_ctk_ast_v1_ExprInfo | null);
  'constructor'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'arguments'?: (_ctk_ast_v1_ExpressionValue)[];
  'constructionKind'?: (_ctk_ast_v1_ConstructionKind);
  'isElidable'?: (boolean);
  'isListInitialization'?: (boolean);
  'isStdInitializerListInitialization'?: (boolean);
  'requiresZeroInitialization'?: (boolean);
  'hadMultipleCandidates'?: (boolean);
  '_constructionKind'?: "constructionKind";
  '_isElidable'?: "isElidable";
  '_isListInitialization'?: "isListInitialization";
  '_isStdInitializerListInitialization'?: "isStdInitializerListInitialization";
  '_requiresZeroInitialization'?: "requiresZeroInitialization";
  '_hadMultipleCandidates'?: "hadMultipleCandidates";
}

export interface CXXConstructExprInfo__Output {
  'expression': (_ctk_ast_v1_ExprInfo__Output | null);
  'constructor': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'arguments': (_ctk_ast_v1_ExpressionValue__Output)[];
  'constructionKind'?: (_ctk_ast_v1_ConstructionKind__Output);
  'isElidable'?: (boolean);
  'isListInitialization'?: (boolean);
  'isStdInitializerListInitialization'?: (boolean);
  'requiresZeroInitialization'?: (boolean);
  'hadMultipleCandidates'?: (boolean);
  '_constructionKind'?: "constructionKind";
  '_isElidable'?: "isElidable";
  '_isListInitialization'?: "isListInitialization";
  '_isStdInitializerListInitialization'?: "isStdInitializerListInitialization";
  '_requiresZeroInitialization'?: "requiresZeroInitialization";
  '_hadMultipleCandidates'?: "hadMultipleCandidates";
}
