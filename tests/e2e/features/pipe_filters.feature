Feature: Pipe filters and tuple callbacks in the console
  Scripts reshape existing values with pipes, preserve native match selections,
  and unpack zip results in collection callbacks and foreach.

  Scenario Outline: A script combines tuple filters and retained native matches
    Given an isolated pipe-filter console and class fixture
    When I execute the complete filter script using the "<engine>" engine
    Then the script prints the expected records and native names

    Examples:
      | engine   |
      | compiled |
      | tree     |

  Scenario Outline: List selection preserves native row handles
    Given an isolated pipe-filter console and class fixture
    When I execute list selection using the "<engine>" engine
    Then selection prints the expected lists and retained field

    Examples:
      | engine   |
      | compiled |
      | tree     |

  Scenario: The interactive prompt executes the complete tuple pipeline
    Given an isolated pipe-filter console and class fixture
    When I paste the tuple pipeline into the real console terminal
    Then the terminal prints the verified tuple pipeline result

  Scenario Outline: Expressions compose across callbacks, calls and file operands
    Given an isolated pipe-filter console and class fixture
    When I execute syntax composition using the "<engine>" engine
    Then composition prints the expected calls and saved records

    Examples:
      | engine   |
      | compiled |
      | tree     |
