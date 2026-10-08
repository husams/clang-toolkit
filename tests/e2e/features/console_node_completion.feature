@e2e
Feature: Prompt completion for native semantic function fields
  Scenario: Projected fields retain their typed schema and native continuation
    Given a private server with native function declarations for completion
    When I complete and inspect native function nodes in the real prompt
    Then the prompt completes projected fields and preserves typed schema and continuation
