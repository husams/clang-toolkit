Feature: Current console editor support
  Scenario: Complete index kinds, highlight commands, edit earlier matcher lines and inspect saved functions
    Given an isolated server for the compiled workspace editor
    When I edit multiline matchers and request saved function help in a real terminal
    Then the workspace preserves later text and shows distinct colors and function signatures
