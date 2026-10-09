Feature: Composable graph values with bounded semantic payloads
  Scenario: Inspect scoped traversal and graph values from a batch
    Given a private server and a graph fixture with a header call
    When I inspect composable graph values through the console
    Then graph fields are typed and header omissions are explicit
