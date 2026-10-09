Feature: Native match results carry source and call-site facts

  Scenario: A selected lambda operator keeps its body calls and caller identity
    Given a private server and source with reasoning facts
    When I query lambda and call-site facts through the console
    Then the console reports complete lambda and static call facts
