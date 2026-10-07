// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { NamedDeclInfo as _ctk_ast_v1_NamedDeclInfo, NamedDeclInfo__Output as _ctk_ast_v1_NamedDeclInfo__Output } from '../../../ctk/ast/v1/NamedDeclInfo.js';
import type { TemplateParameterList as _ctk_ast_v1_TemplateParameterList, TemplateParameterList__Output as _ctk_ast_v1_TemplateParameterList__Output } from '../../../ctk/ast/v1/TemplateParameterList.js';
import type { TemplateArgument as _ctk_ast_v1_TemplateArgument, TemplateArgument__Output as _ctk_ast_v1_TemplateArgument__Output } from '../../../ctk/ast/v1/TemplateArgument.js';

export interface TemplateTemplateParmDecl {
  'named'?: (_ctk_ast_v1_NamedDeclInfo | null);
  'templateParameters'?: (_ctk_ast_v1_TemplateParameterList | null);
  'depth'?: (number);
  'position'?: (number);
  'isParameterPack'?: (boolean);
  'defaultArgument'?: (_ctk_ast_v1_TemplateArgument | null);
  'defaultArgumentWasInherited'?: (boolean);
  'isExpandedParameterPack'?: (boolean);
  'expandedTemplateParameters'?: (_ctk_ast_v1_TemplateParameterList)[];
  '_depth'?: "depth";
  '_position'?: "position";
  '_isParameterPack'?: "isParameterPack";
  '_defaultArgumentWasInherited'?: "defaultArgumentWasInherited";
  '_isExpandedParameterPack'?: "isExpandedParameterPack";
}

export interface TemplateTemplateParmDecl__Output {
  'named': (_ctk_ast_v1_NamedDeclInfo__Output | null);
  'templateParameters': (_ctk_ast_v1_TemplateParameterList__Output | null);
  'depth'?: (number);
  'position'?: (number);
  'isParameterPack'?: (boolean);
  'defaultArgument': (_ctk_ast_v1_TemplateArgument__Output | null);
  'defaultArgumentWasInherited'?: (boolean);
  'isExpandedParameterPack'?: (boolean);
  'expandedTemplateParameters': (_ctk_ast_v1_TemplateParameterList__Output)[];
  '_depth'?: "depth";
  '_position'?: "position";
  '_isParameterPack'?: "isParameterPack";
  '_defaultArgumentWasInherited'?: "defaultArgumentWasInherited";
  '_isExpandedParameterPack'?: "isExpandedParameterPack";
}
