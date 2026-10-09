Feature: Multi-file match values retain typed rows and safe semantic access

  Scenario: Two-file rows retain provenance, continuation, and collection operations
    Given a private server and two source files for reasoning values
    When I query native multi-file values through the console
    Then the console reports per-file rows, continuation, and explicit field availability
