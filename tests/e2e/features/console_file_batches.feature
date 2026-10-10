@e2e
Feature: File inventory and foreground resource batches
  Scenario Outline: File and batch command help is available offline
    Given an offline console client for file resource help
    When I request console help for "<topic>"
    Then the help output includes "<expected>"

    Examples:
      | topic    | expected           |
      | files    | FileSet            |
      | file     | file refresh       |
      | resource | resource status    |
      | batch    | on error stop      |

  Scenario: File and batch statements are parsed as console language
    Given the file resource console grammar
    When I parse the supported resource statements
    Then each statement has its expected command node

  Scenario: Assigned native batch results survive acknowledged group cleanup
    Given an isolated console batch value server with three sources
    When I collect native match values through an assigned console batch and save them
    Then the collected values remain readable with no live native resources

  Scenario: Flattened batch rows retain names after cleanup and persistence
    Given an isolated console batch value server with three sources
    When I flatten native batch results print their names and reload the saved rows
    Then every flattened function name survives with no live native resources
