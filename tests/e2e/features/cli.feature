Feature: Interactive CLI
  Scenario: Asking for help
    Given a CLI connected to the server
    When I enter "help"
    Then the output contains "callgraph"
