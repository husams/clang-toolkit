Feature: Pipe filters and tuple callbacks in the console
  Scripts reshape existing values with pipes, preserve native match selections,
  and unpack zip results in collection callbacks and foreach.

  Scenario Outline: Trailing callable blocks preserve normal calls and native rows
    Given an isolated pipe-filter console and class fixture
    When I execute trailing callable blocks using the "<engine>" engine
    Then trailing blocks print the expected values and retain native matching

    Examples:
      | engine   |
      | compiled |
      | tree     |

  Scenario: Paste trailing callable blocks into the real console terminal
    Given an isolated pipe-filter console and class fixture
    When I paste trailing callable blocks into the real console terminal
    Then the terminal prints the verified trailing pipeline result

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

  Scenario Outline: Type pipeline stages on separate lines without submitting
    Given an isolated pipe-filter console and class fixture
    When I type a multiline pipeline with "<shortcut>" in the "<ui>" console
    Then the pipeline runs once with the expected result

    Examples:
      | shortcut     | ui        |
      | Ctrl+Enter   | workspace |
      | Option+Enter | workspace |
      | Ctrl+Enter   | prompt    |
      | Option+Enter | prompt    |

  Scenario Outline: Expressions compose across callbacks, calls and file operands
    Given an isolated pipe-filter console and class fixture
    When I execute syntax composition using the "<engine>" engine
    Then composition prints the expected calls and saved records

    Examples:
      | engine   |
      | compiled |
      | tree     |

  Scenario: Graph display and inspection preserve retained matching in the real prompt
    Given an isolated pipe-filter console and class fixture
    When I display, inspect and filter a call graph in the real console terminal
    Then graph previews expose structured values and the filtered node still matches
