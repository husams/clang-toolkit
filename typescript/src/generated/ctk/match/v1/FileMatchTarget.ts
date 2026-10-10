// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_service.proto


export interface FileMatchTarget {
  'filePath'?: (string);
  'compileArguments'?: (string)[];
  'workingDirectory'?: (string);
  'compilationDatabase'?: (string);
  'expectedProfileId'?: (string);
  'frozenProfile'?: (boolean);
}

export interface FileMatchTarget__Output {
  'filePath': (string);
  'compileArguments': (string)[];
  'workingDirectory': (string);
  'compilationDatabase': (string);
  'expectedProfileId': (string);
  'frozenProfile': (boolean);
}
