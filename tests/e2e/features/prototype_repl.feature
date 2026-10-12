Feature: Compiled scripts in the interactive REPL
  The compiled prototype engine runs inside both existing console interfaces.

  Scenario: Prompt REPL executes compiled scripts and recovers after errors
    Given an isolated compiled prompt REPL and native sample
    When I exercise compiled scripts through the real prompt terminal
    Then the prompt retains values, runs native continuation, and releases resources

  Scenario: Workspace REPL executes compiled scripts and recovers after errors
    Given an isolated compiled workspace REPL and native sample
    When I exercise compiled scripts through the real workspace terminal
    Then the workspace retains values, runs native continuation, and releases resources
