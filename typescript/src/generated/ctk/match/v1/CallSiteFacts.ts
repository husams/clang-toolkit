// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_result.proto

import type { CallDispatch as _ctk_match_v1_CallDispatch, CallDispatch__Output as _ctk_match_v1_CallDispatch__Output } from '../../../ctk/match/v1/CallDispatch.js';

export interface CallSiteFacts {
  'callerSymbolIdentity'?: (string);
  'callerName'?: (string);
  'dispatch'?: (_ctk_match_v1_CallDispatch);
  'staticCalleeSymbolIdentity'?: (string);
  'staticCalleeName'?: (string);
}

export interface CallSiteFacts__Output {
  'callerSymbolIdentity': (string);
  'callerName': (string);
  'dispatch': (_ctk_match_v1_CallDispatch__Output);
  'staticCalleeSymbolIdentity': (string);
  'staticCalleeName': (string);
}
