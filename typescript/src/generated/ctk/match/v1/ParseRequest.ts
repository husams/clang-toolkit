// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/parse_request.proto

import type { CppSnippet as _ctk_match_v1_CppSnippet, CppSnippet__Output as _ctk_match_v1_CppSnippet__Output } from '../../../ctk/match/v1/CppSnippet.js';

export interface ParseRequest {
  'filePath'?: (string);
  'compileArguments'?: (string)[];
  'workingDirectory'?: (string);
  'compilationDatabase'?: (string);
  'resourceScopeId'?: (string);
  'expectedProfileId'?: (string);
  'frozenProfile'?: (boolean);
  'cppSnippet'?: (_ctk_match_v1_CppSnippet | null);
}

export interface ParseRequest__Output {
  'filePath': (string);
  'compileArguments': (string)[];
  'workingDirectory': (string);
  'compilationDatabase': (string);
  'resourceScopeId': (string);
  'expectedProfileId': (string);
  'frozenProfile': (boolean);
  'cppSnippet': (_ctk_match_v1_CppSnippet__Output | null);
}
