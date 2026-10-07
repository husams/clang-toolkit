// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { AsmOperand as _ctk_ast_v1_AsmOperand, AsmOperand__Output as _ctk_ast_v1_AsmOperand__Output } from '../../../ctk/ast/v1/AsmOperand.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';

export interface GCCAsmStmt {
  'asmString'?: (string);
  'outputs'?: (_ctk_ast_v1_AsmOperand)[];
  'inputs'?: (_ctk_ast_v1_AsmOperand)[];
  'clobbers'?: (string)[];
  'gotoLabels'?: (_ctk_ast_v1_DeclarationSymbol)[];
  'isSimple'?: (boolean);
  'isVolatile'?: (boolean);
  'isGoto'?: (boolean);
  'dialect'?: (string);
  '_asmString'?: "asmString";
  '_isSimple'?: "isSimple";
  '_isVolatile'?: "isVolatile";
  '_isGoto'?: "isGoto";
  '_dialect'?: "dialect";
}

export interface GCCAsmStmt__Output {
  'asmString'?: (string);
  'outputs': (_ctk_ast_v1_AsmOperand__Output)[];
  'inputs': (_ctk_ast_v1_AsmOperand__Output)[];
  'clobbers': (string)[];
  'gotoLabels': (_ctk_ast_v1_DeclarationSymbol__Output)[];
  'isSimple'?: (boolean);
  'isVolatile'?: (boolean);
  'isGoto'?: (boolean);
  'dialect'?: (string);
  '_asmString'?: "asmString";
  '_isSimple'?: "isSimple";
  '_isVolatile'?: "isVolatile";
  '_isGoto'?: "isGoto";
  '_dialect'?: "dialect";
}
