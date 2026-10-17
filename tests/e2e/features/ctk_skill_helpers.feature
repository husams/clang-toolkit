Feature: Use bundled CTK skill utilities through the compiled console
  Scenario: Structured class information and complete or bounded inheritance trees
    Given an isolated server and the bundled CTK helper fixture
    When I query structured classes and inheritance with the imported helpers
    Then the summaries preserve members and paths and expose incomplete or ambiguous results

  Scenario: Reusable matchers and Python-compiled runnable callbacks
    Given an isolated server and the bundled CTK helper fixture
    When I use the ready-made matchers and named and inline callbacks
    Then the documented matchers and executable-block examples return the expected values

  Scenario: Bundled pipe report and tuple callback compatibility
    Given an isolated server and the bundled CTK helper fixture
    When I run the bundled pipe report and tuple callbacks in both engines
    Then the report output and whole-item compatibility match the skill examples

  Scenario: Live class lookup and template inheritance in both execution engines
    Given an isolated server and the bundled CTK template fixture
    When I select live classes and inspect their template specializations in both engines
    Then the live nodes and template summaries preserve specialization identity and complete ancestors
