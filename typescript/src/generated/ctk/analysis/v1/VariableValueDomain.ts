// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/variable_flow.proto

export const VariableValueDomain = {
  VARIABLE_VALUE_DOMAIN_UNSPECIFIED: 'VARIABLE_VALUE_DOMAIN_UNSPECIFIED',
  INTERVAL: 'INTERVAL',
} as const;

export type VariableValueDomain =
  | 'VARIABLE_VALUE_DOMAIN_UNSPECIFIED'
  | 0
  | 'INTERVAL'
  | 1

export type VariableValueDomain__Output = typeof VariableValueDomain[keyof typeof VariableValueDomain]
