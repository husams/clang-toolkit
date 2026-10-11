@e2e
Feature: Durable server-owned batch SDK
  Scenario: Async SDK runs survive client reconnect and expose detached final values
    Given an isolated durable batch server with a source file
    When I start and wait for a durable batch through the async SDK
    Then a new sync client can read its final detached group values
