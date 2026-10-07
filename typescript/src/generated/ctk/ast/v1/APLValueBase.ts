// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { Empty as _ctk_ast_v1_Empty, Empty__Output as _ctk_ast_v1_Empty__Output } from '../../../ctk/ast/v1/Empty.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { APTypeInfoLValue as _ctk_ast_v1_APTypeInfoLValue, APTypeInfoLValue__Output as _ctk_ast_v1_APTypeInfoLValue__Output } from '../../../ctk/ast/v1/APTypeInfoLValue.js';
import type { APDynamicAllocation as _ctk_ast_v1_APDynamicAllocation, APDynamicAllocation__Output as _ctk_ast_v1_APDynamicAllocation__Output } from '../../../ctk/ast/v1/APDynamicAllocation.js';

export interface APLValueBase {
  'nullBase'?: (_ctk_ast_v1_Empty | null);
  'declaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'expression'?: (_ctk_ast_v1_ExpressionValue | null);
  'typeInfo'?: (_ctk_ast_v1_APTypeInfoLValue | null);
  'dynamicAllocation'?: (_ctk_ast_v1_APDynamicAllocation | null);
  'value'?: "nullBase"|"declaration"|"expression"|"typeInfo"|"dynamicAllocation";
}

export interface APLValueBase__Output {
  'nullBase'?: (_ctk_ast_v1_Empty__Output | null);
  'declaration'?: (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'expression'?: (_ctk_ast_v1_ExpressionValue__Output | null);
  'typeInfo'?: (_ctk_ast_v1_APTypeInfoLValue__Output | null);
  'dynamicAllocation'?: (_ctk_ast_v1_APDynamicAllocation__Output | null);
  'value'?: "nullBase"|"declaration"|"expression"|"typeInfo"|"dynamicAllocation";
}
