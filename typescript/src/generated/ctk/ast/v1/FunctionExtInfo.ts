// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { FunctionCallingConvention as _ctk_ast_v1_FunctionCallingConvention, FunctionCallingConvention__Output as _ctk_ast_v1_FunctionCallingConvention__Output } from '../../../ctk/ast/v1/FunctionCallingConvention.js';

export interface FunctionExtInfo {
  'callingConvention'?: (_ctk_ast_v1_FunctionCallingConvention);
  'targetConventionName'?: (string);
  'noReturn'?: (boolean);
  'producesResult'?: (boolean);
  'regparm'?: (number);
  'noCallerSavedRegisters'?: (boolean);
  'noCfCheck'?: (boolean);
  'cmseNonsecureCall'?: (boolean);
  '_callingConvention'?: "callingConvention";
  '_targetConventionName'?: "targetConventionName";
  '_noReturn'?: "noReturn";
  '_producesResult'?: "producesResult";
  '_regparm'?: "regparm";
  '_noCallerSavedRegisters'?: "noCallerSavedRegisters";
  '_noCfCheck'?: "noCfCheck";
  '_cmseNonsecureCall'?: "cmseNonsecureCall";
}

export interface FunctionExtInfo__Output {
  'callingConvention'?: (_ctk_ast_v1_FunctionCallingConvention__Output);
  'targetConventionName'?: (string);
  'noReturn'?: (boolean);
  'producesResult'?: (boolean);
  'regparm'?: (number);
  'noCallerSavedRegisters'?: (boolean);
  'noCfCheck'?: (boolean);
  'cmseNonsecureCall'?: (boolean);
  '_callingConvention'?: "callingConvention";
  '_targetConventionName'?: "targetConventionName";
  '_noReturn'?: "noReturn";
  '_producesResult'?: "producesResult";
  '_regparm'?: "regparm";
  '_noCallerSavedRegisters'?: "noCallerSavedRegisters";
  '_noCfCheck'?: "noCfCheck";
  '_cmseNonsecureCall'?: "cmseNonsecureCall";
}
