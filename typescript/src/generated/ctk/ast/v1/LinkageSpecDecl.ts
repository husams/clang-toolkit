// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclInfo as _ctk_ast_v1_DeclInfo, DeclInfo__Output as _ctk_ast_v1_DeclInfo__Output } from '../../../ctk/ast/v1/DeclInfo.js';
import type { DeclLinkageLanguage as _ctk_ast_v1_DeclLinkageLanguage, DeclLinkageLanguage__Output as _ctk_ast_v1_DeclLinkageLanguage__Output } from '../../../ctk/ast/v1/DeclLinkageLanguage.js';
import type { DeclarationValue as _ctk_ast_v1_DeclarationValue, DeclarationValue__Output as _ctk_ast_v1_DeclarationValue__Output } from '../../../ctk/ast/v1/DeclarationValue.js';

export interface LinkageSpecDecl {
  'declaration'?: (_ctk_ast_v1_DeclInfo | null);
  'language'?: (_ctk_ast_v1_DeclLinkageLanguage);
  'declarations'?: (_ctk_ast_v1_DeclarationValue)[];
  '_language'?: "language";
}

export interface LinkageSpecDecl__Output {
  'declaration': (_ctk_ast_v1_DeclInfo__Output | null);
  'language'?: (_ctk_ast_v1_DeclLinkageLanguage__Output);
  'declarations': (_ctk_ast_v1_DeclarationValue__Output)[];
  '_language'?: "language";
}
