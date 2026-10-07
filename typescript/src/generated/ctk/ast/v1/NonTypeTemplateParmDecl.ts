// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclaratorDeclInfo as _ctk_ast_v1_DeclaratorDeclInfo, DeclaratorDeclInfo__Output as _ctk_ast_v1_DeclaratorDeclInfo__Output } from '../../../ctk/ast/v1/DeclaratorDeclInfo.js';
import type { TemplateArgument as _ctk_ast_v1_TemplateArgument, TemplateArgument__Output as _ctk_ast_v1_TemplateArgument__Output } from '../../../ctk/ast/v1/TemplateArgument.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { TypeConstraint as _ctk_ast_v1_TypeConstraint, TypeConstraint__Output as _ctk_ast_v1_TypeConstraint__Output } from '../../../ctk/ast/v1/TypeConstraint.js';

export interface NonTypeTemplateParmDecl {
  'declarator'?: (_ctk_ast_v1_DeclaratorDeclInfo | null);
  'depth'?: (number);
  'position'?: (number);
  'isParameterPack'?: (boolean);
  'defaultArgument'?: (_ctk_ast_v1_TemplateArgument | null);
  'defaultArgumentWasInherited'?: (boolean);
  'isPackExpansion'?: (boolean);
  'expandedParameterTypes'?: (_ctk_ast_v1_QualType)[];
  'typeConstraint'?: (_ctk_ast_v1_TypeConstraint | null);
  '_depth'?: "depth";
  '_position'?: "position";
  '_isParameterPack'?: "isParameterPack";
  '_defaultArgumentWasInherited'?: "defaultArgumentWasInherited";
  '_isPackExpansion'?: "isPackExpansion";
}

export interface NonTypeTemplateParmDecl__Output {
  'declarator': (_ctk_ast_v1_DeclaratorDeclInfo__Output | null);
  'depth'?: (number);
  'position'?: (number);
  'isParameterPack'?: (boolean);
  'defaultArgument': (_ctk_ast_v1_TemplateArgument__Output | null);
  'defaultArgumentWasInherited'?: (boolean);
  'isPackExpansion'?: (boolean);
  'expandedParameterTypes': (_ctk_ast_v1_QualType__Output)[];
  'typeConstraint': (_ctk_ast_v1_TypeConstraint__Output | null);
  '_depth'?: "depth";
  '_position'?: "position";
  '_isParameterPack'?: "isParameterPack";
  '_defaultArgumentWasInherited'?: "defaultArgumentWasInherited";
  '_isPackExpansion'?: "isPackExpansion";
}
