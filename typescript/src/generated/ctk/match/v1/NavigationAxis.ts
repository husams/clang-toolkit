// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/match/v1/match_service.proto

export const NavigationAxis = {
  NAVIGATION_AXIS_UNSPECIFIED: 'NAVIGATION_AXIS_UNSPECIFIED',
  NAVIGATION_AXIS_CHILDREN: 'NAVIGATION_AXIS_CHILDREN',
  NAVIGATION_AXIS_PARENTS: 'NAVIGATION_AXIS_PARENTS',
} as const;

export type NavigationAxis =
  | 'NAVIGATION_AXIS_UNSPECIFIED'
  | 0
  | 'NAVIGATION_AXIS_CHILDREN'
  | 1
  | 'NAVIGATION_AXIS_PARENTS'
  | 2

export type NavigationAxis__Output = typeof NavigationAxis[keyof typeof NavigationAxis]
