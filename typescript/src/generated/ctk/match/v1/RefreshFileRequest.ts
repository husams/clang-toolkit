// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/resources.proto


export interface RefreshFileRequest {
  'leaseId'?: (string);
  'sessionId'?: (string);
  'resourceScopeId'?: (string);
  'handle'?: "leaseId"|"sessionId";
}

export interface RefreshFileRequest__Output {
  'leaseId'?: (string);
  'sessionId'?: (string);
  'resourceScopeId': (string);
  'handle'?: "leaseId"|"sessionId";
}
