Feature: Background project symbol lookup
  Scenario: Console lists indexed projects and server status includes their progress
    Given an isolated server and three translation units with a shared header
    Then the console lists zero indexed projects
    When I index the project and pause background refresh through gRPC
    Then the console lists the indexed project and server status shows its coverage

  Scenario: UI clients control selective indexing without blocking native work
    Given an isolated server and three translation units with a shared header
    When I index the project and pause background refresh through gRPC
    Then symbol lookup remains available and foreground parsing still works
    When I edit the shared header and resume background refresh through gRPC
    Then only dependent translation units are reindexed and new symbols are found

  Scenario: Failed refresh keeps committed symbols and resumes after repair
    Given an isolated server and three translation units with a shared header
    When I index the project and pause background refresh through gRPC
    When I introduce an invalid header and resume indexing
    Then prior symbols remain available with stale coverage until the header is repaired

  Scenario: Foreground requests remain responsive during active extraction
    Given an isolated server and three translation units with a shared header
    When I index the project and pause background refresh through gRPC
    Then status controls and native parsing respond during a large TU refresh

  Scenario: Multiple projects stay monitored with independent controls
    Given an isolated server and three translation units with a shared header
    When I start monitoring two projects through the console
    Then both projects refresh and cancelling one leaves the other monitored

  Scenario: Console searches name prefixes across every indexed project
    Given an isolated server and three translation units with a shared header
    When I index the project and pause background refresh through gRPC
    Then the console searches partial names globally and within a project

  Scenario: Console optionally filters symbol kinds before limiting results
    Given an isolated server and three translation units with a shared header
    When I index the project and pause background refresh through gRPC
    Then kind filtering works in scoped and global console searches with kinds in results

  Scenario: Alias searches return shared header symbols once per project
    Given an isolated server and three translation units with a shared header
    When I index the project and pause background refresh through gRPC
    Then alias searches retain kinds and return each shared definition once per project
