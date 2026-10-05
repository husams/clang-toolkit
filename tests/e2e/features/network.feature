Feature: gRPC network client
  Scenario Outline: Query over the configured local transport
    Given a query server using <transport>
    And a C++ file containing a declaration
    When I run the declaration query
    Then the stream contains a match and successful completion

    Examples:
      | transport |
      | unix      |
      | tcp       |

  Scenario: Bidirectional query session half-closes after matching
    Given a query server using unix
    And a C++ file containing a declaration
    When I run the query through a bidirectional session
    Then the session stream contains a match and completion

  Scenario: Bidirectional session rejects a second query definition
    Given a query server using unix
    When I define two queries in one bidirectional session
    Then the session reports a command rejection

  Scenario: Bidirectional session can be cancelled
    Given a query server using unix
    When I cancel an active bidirectional session
    Then the session reports cancellation

  Scenario: A later limited file batch is rejected while accepted work completes
    Given a query server with a one-file limit
    And a C++ file containing a declaration
    When I match the first file and add a second file
    Then the second batch is rejected while the first file completes
