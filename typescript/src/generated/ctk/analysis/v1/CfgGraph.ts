// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/cfg_graph.proto

import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { CfgBlock as _ctk_analysis_v1_CfgBlock, CfgBlock__Output as _ctk_analysis_v1_CfgBlock__Output } from '../../../ctk/analysis/v1/CfgBlock.js';
import type { FieldAvailability as _ctk_ast_v1_FieldAvailability, FieldAvailability__Output as _ctk_ast_v1_FieldAvailability__Output } from '../../../ctk/ast/v1/FieldAvailability.js';
import type { Long } from '@grpc/proto-loader';

export interface CfgGraph {
  'function'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'entryBlock'?: (number | string | Long);
  'exitBlock'?: (number | string | Long);
  'blocks'?: (_ctk_analysis_v1_CfgBlock)[];
  'isLinear'?: (boolean);
  'isComplete'?: (boolean);
  'availability'?: (_ctk_ast_v1_FieldAvailability)[];
  '_isComplete'?: "isComplete";
}

export interface CfgGraph__Output {
  'function': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'entryBlock': (string);
  'exitBlock': (string);
  'blocks': (_ctk_analysis_v1_CfgBlock__Output)[];
  'isLinear': (boolean);
  'isComplete'?: (boolean);
  'availability': (_ctk_ast_v1_FieldAvailability__Output)[];
  '_isComplete'?: "isComplete";
}
