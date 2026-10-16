Feature: Agents run bundled CFG and local-variable recipes
  Scenario Outline: Ready-made flow recipes run outside the project checkout
    Given an isolated flow-script fixture with the <engine> engine
    When I run the bundled CFG, usage and value-range scripts with named arguments
    Then the stream, exported facts and loop ranges describe the supplied fixture

    Examples:
      | engine   |
      | compiled |
      | tree     |

  Scenario: Selection errors and unsupported arithmetic stay explicit
    Given an isolated flow-script fixture with the compiled engine
    When I run the recipes with missing or ambiguous selections and unsupported arithmetic
    Then failed selections export no report and unsupported ranges remain incomplete
