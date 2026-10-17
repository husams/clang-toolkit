Feature: Background project symbol lookup
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
