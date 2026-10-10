Feature: Native match results carry source and call-site facts

  Scenario: A selected lambda operator keeps its body calls and caller identity
    Given a private server and source with reasoning facts
    When I query lambda and call-site facts through the console
    Then the console reports complete lambda and static call facts

  Scenario: Byte offsets delimit editable source slices
    Given a private server and source with reasoning facts
    When I query byte offsets and exclusive range ends through the console
    Then the offsets select complete source bytes including macro invocations
