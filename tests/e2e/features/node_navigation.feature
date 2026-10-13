Feature: Navigate from retained bound nodes
  Scenario Outline: Immediate neighbours and movement preserve native references
    Given a navigation server using <transport>
    When I peek children and move down and up from retained bindings
    Then immediate filtering, streaming, continued matching and source ownership hold

    Examples:
      | transport |
      | unix      |
      | tcp       |

  Scenario Outline: Match scope children uses native immediate candidates
    Given a navigation server using <transport>
    When I match immediate children with an explicit scope
    Then scoped matches stream and preserve named native bindings

    Examples:
      | transport |
      | unix      |
      | tcp       |
