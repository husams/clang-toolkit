Feature: Noninteractive reasoning batches
  Scenario: Run a multiline match batch against the private RPC server
    Given a private server and a tiny batch fixture
    When I execute the fixture through the CLI batch path
    Then the batch prints both function names without a prompt
