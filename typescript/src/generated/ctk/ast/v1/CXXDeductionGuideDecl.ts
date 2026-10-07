// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { FunctionDeclInfo as _ctk_ast_v1_FunctionDeclInfo, FunctionDeclInfo__Output as _ctk_ast_v1_FunctionDeclInfo__Output } from '../../../ctk/ast/v1/FunctionDeclInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { DeclDeductionCandidateKind as _ctk_ast_v1_DeclDeductionCandidateKind, DeclDeductionCandidateKind__Output as _ctk_ast_v1_DeclDeductionCandidateKind__Output } from '../../../ctk/ast/v1/DeclDeductionCandidateKind.js';
import type { DeclSourceDeductionGuideKind as _ctk_ast_v1_DeclSourceDeductionGuideKind, DeclSourceDeductionGuideKind__Output as _ctk_ast_v1_DeclSourceDeductionGuideKind__Output } from '../../../ctk/ast/v1/DeclSourceDeductionGuideKind.js';

export interface CXXDeductionGuideDecl {
  'function'?: (_ctk_ast_v1_FunctionDeclInfo | null);
  'deducedTemplate'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'deductionCandidateKind'?: (_ctk_ast_v1_DeclDeductionCandidateKind);
  'correspondingConstructor'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'sourceDeductionGuide'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'sourceKind'?: (_ctk_ast_v1_DeclSourceDeductionGuideKind);
  '_deductionCandidateKind'?: "deductionCandidateKind";
  '_sourceKind'?: "sourceKind";
}

export interface CXXDeductionGuideDecl__Output {
  'function': (_ctk_ast_v1_FunctionDeclInfo__Output | null);
  'deducedTemplate': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'deductionCandidateKind'?: (_ctk_ast_v1_DeclDeductionCandidateKind__Output);
  'correspondingConstructor': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'sourceDeductionGuide': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'sourceKind'?: (_ctk_ast_v1_DeclSourceDeductionGuideKind__Output);
  '_deductionCandidateKind'?: "deductionCandidateKind";
  '_sourceKind'?: "sourceKind";
}
