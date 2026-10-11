Feature: Optional console workspace
  The workspace uses the existing console language and a real server.

  Scenario: Browse files, expand printed collections, and execute multiline analysis in the workspace
    Given an isolated workspace server and a C++ input
    When I use the real workspace menu and file panel then submit multiline analysis
    Then the workspace shows native results and records each command once

  Scenario: Reject a workspace presentation for piped scripts
    When I request the workspace with a piped script
    Then the command explains that the workspace requires interactive input
