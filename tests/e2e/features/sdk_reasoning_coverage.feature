Feature: Positive semantic coverage through the native Python SDK

  Scenario: Sync and async SDKs preserve declaration, CFG, and base facts
    Given a private server and source with SDK reasoning facts
    When I query the reasoning facts through both SDK clients
    Then both SDK clients return the same positive semantic facts
