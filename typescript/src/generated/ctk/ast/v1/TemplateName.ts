// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { OverloadedTemplateName as _ctk_ast_v1_OverloadedTemplateName, OverloadedTemplateName__Output as _ctk_ast_v1_OverloadedTemplateName__Output } from '../../../ctk/ast/v1/OverloadedTemplateName.js';
import type { DeclarationName as _ctk_ast_v1_DeclarationName, DeclarationName__Output as _ctk_ast_v1_DeclarationName__Output } from '../../../ctk/ast/v1/DeclarationName.js';
import type { QualifiedTemplateName as _ctk_ast_v1_QualifiedTemplateName, QualifiedTemplateName__Output as _ctk_ast_v1_QualifiedTemplateName__Output } from '../../../ctk/ast/v1/QualifiedTemplateName.js';
import type { DependentTemplateName as _ctk_ast_v1_DependentTemplateName, DependentTemplateName__Output as _ctk_ast_v1_DependentTemplateName__Output } from '../../../ctk/ast/v1/DependentTemplateName.js';
import type { SubstitutedTemplateName as _ctk_ast_v1_SubstitutedTemplateName, SubstitutedTemplateName__Output as _ctk_ast_v1_SubstitutedTemplateName__Output } from '../../../ctk/ast/v1/SubstitutedTemplateName.js';
import type { SubstitutedTemplatePack as _ctk_ast_v1_SubstitutedTemplatePack, SubstitutedTemplatePack__Output as _ctk_ast_v1_SubstitutedTemplatePack__Output } from '../../../ctk/ast/v1/SubstitutedTemplatePack.js';
import type { DeducedTemplateName as _ctk_ast_v1_DeducedTemplateName, DeducedTemplateName__Output as _ctk_ast_v1_DeducedTemplateName__Output } from '../../../ctk/ast/v1/DeducedTemplateName.js';
import type { Empty as _ctk_ast_v1_Empty, Empty__Output as _ctk_ast_v1_Empty__Output } from '../../../ctk/ast/v1/Empty.js';

export interface TemplateName {
  'declaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'overload'?: (_ctk_ast_v1_OverloadedTemplateName | null);
  'assumed'?: (_ctk_ast_v1_DeclarationName | null);
  'qualified'?: (_ctk_ast_v1_QualifiedTemplateName | null);
  'dependent'?: (_ctk_ast_v1_DependentTemplateName | null);
  'substituted'?: (_ctk_ast_v1_SubstitutedTemplateName | null);
  'substitutedPack'?: (_ctk_ast_v1_SubstitutedTemplatePack | null);
  'usingShadow'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'deduced'?: (_ctk_ast_v1_DeducedTemplateName | null);
  'nullName'?: (_ctk_ast_v1_Empty | null);
  'value'?: "declaration"|"overload"|"assumed"|"qualified"|"dependent"|"substituted"|"substitutedPack"|"usingShadow"|"deduced"|"nullName";
}

export interface TemplateName__Output {
  'declaration'?: (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'overload'?: (_ctk_ast_v1_OverloadedTemplateName__Output | null);
  'assumed'?: (_ctk_ast_v1_DeclarationName__Output | null);
  'qualified'?: (_ctk_ast_v1_QualifiedTemplateName__Output | null);
  'dependent'?: (_ctk_ast_v1_DependentTemplateName__Output | null);
  'substituted'?: (_ctk_ast_v1_SubstitutedTemplateName__Output | null);
  'substitutedPack'?: (_ctk_ast_v1_SubstitutedTemplatePack__Output | null);
  'usingShadow'?: (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'deduced'?: (_ctk_ast_v1_DeducedTemplateName__Output | null);
  'nullName'?: (_ctk_ast_v1_Empty__Output | null);
  'value'?: "declaration"|"overload"|"assumed"|"qualified"|"dependent"|"substituted"|"substitutedPack"|"usingShadow"|"deduced"|"nullName";
}
