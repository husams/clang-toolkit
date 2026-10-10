Feature: Durable server-owned native batch runs
  Scenario: Background runs survive caller disconnect and preserve frozen groups
    Given an isolated durable batch server with five translation units
    When I start a native batch and disconnect its caller
    Then the durable results agree with serial matching and resources are released

  Scenario: Completed manifests and export receipts survive server restart
    Given an isolated durable batch server with five translation units
    When I complete an exported native batch and restart the server
    Then status retains the results and committed exports without replay

  Scenario: Native batch expressions collect values after each scope closes
    Given an isolated durable batch server with five translation units
    When I evaluate a batch through the native script API
    Then native expression results are detached and group cleanup is acknowledged

  Scenario: Known failed groups can retry after acknowledged cleanup
    Given an isolated durable batch server with five translation units
    When I retry a known failed export after repairing its destination
    Then all retried groups complete with committed exports

  Scenario: Retry validates consumed dependency closure atomically
    Given an isolated durable batch server with five translation units
    When I change a consumed header before retrying a failed group
    Then retry rejects the changed dependency without mutating the run

  Scenario: Cancellation preserves pending work for resume and known work for retry
    Given an isolated durable batch server with five translation units
    When I cancel admitted native work and resume the durable run
    Then pending and cancelled groups eventually complete without leaked ownership

  Scenario: Process loss preserves unknown outcomes without automatic replay
    Given an isolated durable batch server with five translation units
    When I kill the server during admitted native work and restart it
    Then the interrupted group is unknown and cannot be silently resumed
