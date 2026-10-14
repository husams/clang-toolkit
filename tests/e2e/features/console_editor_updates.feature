Feature: Current console editor support
  Scenario: Edit earlier matcher lines and inspect saved functions in the workspace
    Given an isolated server for the compiled workspace editor
    When I edit multiline matchers and request saved function help in a real terminal
    Then the workspace preserves later text and shows distinct colors and function signatures
