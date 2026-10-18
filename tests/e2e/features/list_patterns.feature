Feature: List destructuring and multi-clause console functions
  Scenario Outline: Execute list patterns in a real console terminal
    Given an isolated list-pattern console
    When I run the list-pattern example in the "<engine>" terminal
    Then the terminal prints the list-pattern results

    Examples:
      | engine   |
      | compiled |
      | tree     |

  Scenario Outline: Execute general recursive list functions in a real console terminal
    Given an isolated list-pattern console
    When I run the recursive-list example in the "<engine>" terminal
    Then the terminal prints recursive map filter and reverse results

    Examples:
      | engine   |
      | compiled |
      | tree     |
