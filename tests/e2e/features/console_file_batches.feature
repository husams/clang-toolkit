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
