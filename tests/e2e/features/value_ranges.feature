Feature: Retained local value ranges
  Scenario Outline: Track numeric bounds through the Page loop and branches
    Given an isolated value interval server using <transport>
    When I analyze the loop ranges with retained nodes and the console
    Then the numeric facts match the loop invariant and capped branches

    Examples:
      | transport |
      | unix      |
      | tcp       |
