Feature: Native opened files and bounded batches
  Scenario: Discovered profiles and explicit leases preserve independent immutable cursors
    Given an isolated opened-file server and changing sources
    When I discover open refresh and independently close native file resources
    Then file identities and independent pins remain correct

  Scenario: Foreground batches process more inputs than the server admission limit
    Given an isolated opened-file server with a two-input admission limit
    When I run real console size and count batches with detached exports
    Then every group finishes with acknowledged cleanup and no native resources escape

  Scenario: A lost unary reply still has server-owned scope cleanup
    Given an isolated opened-file server with a small client reply limit
    When a scoped unary match commits but its reply exceeds the transport limit
    Then releasing the scope acknowledges all provisional resources were closed

  Scenario: Atomic admission preserves resources borrowed before a scope
    Given an isolated opened-file server with a two-input admission limit
    When I reject an oversized scope and release a scope borrowing an existing snapshot
    Then admission is atomic and external result pins survive acknowledged cleanup

  Scenario: Detached native analyses share the frozen resource scope
    Given an isolated opened-file server and changing sources
    When I execute every detached native analysis under a frozen resource scope
    Then detached analyses account for their snapshots and release transient reuse

  Scenario: Stop and continue policies preserve completed exports and clean failed groups
    Given an isolated opened-file server with a two-input admission limit
    When I fail batch bodies after exporting under stop and continue policies
    Then failure status preserves exports while every accepted group acknowledges cleanup
