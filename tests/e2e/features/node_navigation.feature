Feature: Navigate from retained bound nodes
  Scenario Outline: Immediate neighbours and movement preserve native references
    Given a navigation server using <transport>
    When I peek children and move down and up from retained bindings
    Then immediate filtering, streaming, continued matching and source ownership hold

    Examples:
      | transport |
      | unix      |
      | tcp       |
