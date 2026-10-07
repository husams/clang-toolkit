// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { AsmOperand as _ctk_ast_v1_AsmOperand, AsmOperand__Output as _ctk_ast_v1_AsmOperand__Output } from '../../../ctk/ast/v1/AsmOperand.js';

export interface MSAsmStmt {
  'asmString'?: (string);
  'outputs'?: (_ctk_ast_v1_AsmOperand)[];
  'inputs'?: (_ctk_ast_v1_AsmOperand)[];
  'clobbers'?: (string)[];
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

export interface MSAsmStmt__Output {
  'asmString'?: (string);
  'outputs': (_ctk_ast_v1_AsmOperand__Output)[];
  'inputs': (_ctk_ast_v1_AsmOperand__Output)[];
  'clobbers': (string)[];
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
