Feature: Stream traversal from retained native nodes
  Scenario Outline: Parsed trees and non-declaration bindings stream without reparsing
    Given a query server using <transport>
    And a native traversal fixture with types and inheritance
    When I stream visits from the parsed tree and its retained bindings
    Then visits precede completion and every native root remains reusable

    Examples:
      | transport |
      | unix      |
      | tcp       |

  Scenario: Traversal streams beyond the individual message limit
    Given a traversal server with a small message limit and many nodes
    When I consume a traversal whose visits exceed one message
    Then each visit fits and the complete stream exceeds the message limit
