Feature: Multi-file match values retain typed rows and safe semantic access

  Scenario: Two-file rows retain provenance, continuation, and collection operations
    Given a private server and two source files for reasoning values
    When I query native multi-file values through the console
    Then the console reports per-file rows, continuation, and explicit field availability

  Scenario: Direct directory and glob inputs retain ordered parallel match results
    Given a private server and two source files for reasoning values
    When I match directory and glob inputs through the console and async SDK
    Then directory and glob results preserve single-file behavior and continuation

  Scenario: Match statement blocks expose streamed bindings in a local row scope
    Given a private server and two source files for reasoning values
    When I run streamed match blocks through the console and SDKs
    Then binding fields and nested statements work without leaking row locals
