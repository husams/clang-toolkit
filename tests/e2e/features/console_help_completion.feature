@e2e
Feature: Detailed help and contextual filesystem completion
  Scenario Outline: Command help without a running server
    Given an offline interactive console
    When I submit help text "<command>" through the prompt
    Then detailed help contains "<usage>"

    Examples:
      | command          | usage                 |
      | help parse       | parse PATH            |
      | match?           | match MATCHER         |
      | help?            | help [command         |
      | help cursor open | cursor open PATH      |
      | cursor open?     | cursor open PATH      |
      | help in          | in parse PATH         |
      | yield?           | yield VALUE           |

  Scenario: Unknown help topic is local
    Given an offline interactive console
    When I submit help text "cursor missing?" through the prompt
    Then help reports an unknown topic

  Scenario: Tab finishes a filename containing spaces from an unfinished quote
    Given console files with spaces
    When I complete the unfinished path through the prompt
    Then the submitted sentence is a valid quoted parse command

  Scenario: Tab continues navigation after selecting a quoted directory
    Given console files with spaces
    When I navigate a directory and complete its child through the prompt
    Then the submitted sentence selects the child file

  Scenario: Completed filename reaches native parse and match
    Given a native server for console completion
    And console files with spaces
    When I complete the unfinished path and execute declarative analysis
    Then native analysis finds the declared function
