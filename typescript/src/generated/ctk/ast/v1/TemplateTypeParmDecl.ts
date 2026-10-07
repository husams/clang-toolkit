// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeDeclInfo as _ctk_ast_v1_TypeDeclInfo, TypeDeclInfo__Output as _ctk_ast_v1_TypeDeclInfo__Output } from '../../../ctk/ast/v1/TypeDeclInfo.js';
import type { TemplateArgument as _ctk_ast_v1_TemplateArgument, TemplateArgument__Output as _ctk_ast_v1_TemplateArgument__Output } from '../../../ctk/ast/v1/TemplateArgument.js';
import type { TypeConstraint as _ctk_ast_v1_TypeConstraint, TypeConstraint__Output as _ctk_ast_v1_TypeConstraint__Output } from '../../../ctk/ast/v1/TypeConstraint.js';

export interface TemplateTypeParmDecl {
  'typeDeclaration'?: (_ctk_ast_v1_TypeDeclInfo | null);
  'depth'?: (number);
  'position'?: (number);
  'isParameterPack'?: (boolean);
  'defaultArgument'?: (_ctk_ast_v1_TemplateArgument | null);
  'defaultArgumentWasInherited'?: (boolean);
  'typeConstraint'?: (_ctk_ast_v1_TypeConstraint | null);
  'isPackExpansion'?: (boolean);
  '_depth'?: "depth";
  '_position'?: "position";
  '_isParameterPack'?: "isParameterPack";
  '_defaultArgumentWasInherited'?: "defaultArgumentWasInherited";
  '_isPackExpansion'?: "isPackExpansion";
}

export interface TemplateTypeParmDecl__Output {
  'typeDeclaration': (_ctk_ast_v1_TypeDeclInfo__Output | null);
  'depth'?: (number);
  'position'?: (number);
  'isParameterPack'?: (boolean);
  'defaultArgument': (_ctk_ast_v1_TemplateArgument__Output | null);
  'defaultArgumentWasInherited'?: (boolean);
  'typeConstraint': (_ctk_ast_v1_TypeConstraint__Output | null);
  'isPackExpansion'?: (boolean);
  '_depth'?: "depth";
  '_position'?: "position";
  '_isParameterPack'?: "isParameterPack";
  '_defaultArgumentWasInherited'?: "defaultArgumentWasInherited";
  '_isPackExpansion'?: "isPackExpansion";
}
