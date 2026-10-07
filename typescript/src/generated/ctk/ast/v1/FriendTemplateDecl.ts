// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclInfo as _ctk_ast_v1_DeclInfo, DeclInfo__Output as _ctk_ast_v1_DeclInfo__Output } from '../../../ctk/ast/v1/DeclInfo.js';
import type { TemplateParameterList as _ctk_ast_v1_TemplateParameterList, TemplateParameterList__Output as _ctk_ast_v1_TemplateParameterList__Output } from '../../../ctk/ast/v1/TemplateParameterList.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';

export interface FriendTemplateDecl {
  'declaration'?: (_ctk_ast_v1_DeclInfo | null);
  'templateParameters'?: (_ctk_ast_v1_TemplateParameterList)[];
  'friendDeclaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'isDescribedTemplate'?: (boolean);
  'friendType'?: (_ctk_ast_v1_QualType | null);
  '_isDescribedTemplate'?: "isDescribedTemplate";
}

export interface FriendTemplateDecl__Output {
  'declaration': (_ctk_ast_v1_DeclInfo__Output | null);
  'templateParameters': (_ctk_ast_v1_TemplateParameterList__Output)[];
  'friendDeclaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'isDescribedTemplate'?: (boolean);
  'friendType': (_ctk_ast_v1_QualType__Output | null);
  '_isDescribedTemplate'?: "isDescribedTemplate";
}
