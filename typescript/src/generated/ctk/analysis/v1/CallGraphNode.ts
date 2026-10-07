// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/call_graph_node.proto

import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { DeclarationValue as _ctk_ast_v1_DeclarationValue, DeclarationValue__Output as _ctk_ast_v1_DeclarationValue__Output } from '../../../ctk/ast/v1/DeclarationValue.js';
import type { FieldAvailability as _ctk_ast_v1_FieldAvailability, FieldAvailability__Output as _ctk_ast_v1_FieldAvailability__Output } from '../../../ctk/ast/v1/FieldAvailability.js';
import type { Long } from '@grpc/proto-loader';

export interface CallGraphNode {
  'nodeIndex'?: (number | string | Long);
  'isVirtualRoot'?: (boolean);
  'function'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'anonymousDeclaration'?: (_ctk_ast_v1_DeclarationValue | null);
  'hasDefinition'?: (boolean);
  'declarationKind'?: (string);
  'isComplete'?: (boolean);
  'availability'?: (_ctk_ast_v1_FieldAvailability)[];
  '_isComplete'?: "isComplete";
}

export interface CallGraphNode__Output {
  'nodeIndex': (string);
  'isVirtualRoot': (boolean);
  'function': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'anonymousDeclaration': (_ctk_ast_v1_DeclarationValue__Output | null);
  'hasDefinition': (boolean);
  'declarationKind': (string);
  'isComplete'?: (boolean);
  'availability': (_ctk_ast_v1_FieldAvailability__Output)[];
  '_isComplete'?: "isComplete";
}
