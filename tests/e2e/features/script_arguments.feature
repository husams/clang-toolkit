Feature: Run console scripts with named arguments
  Scenario Outline: Pass literal values to a script using <mode> input
    Given a private server and a parameterized script fixture
    When I run the parameterized script using <mode> input
    Then its arguments select native matches and preserve literal values without a prompt

    Examples:
      | mode       |
      | positional |
      | explicit   |
      | inline     |
      | stdin      |
