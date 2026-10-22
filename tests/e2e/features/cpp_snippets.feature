Feature: Analyze temporary C++ snippets using project compilation settings
  Scenario: Borrow a named source file and retain instantiated template analysis
    Given an isolated snippet project with distinct compilation commands
    When I parse a template snippet using the named source settings
    Then the retained snippet exposes the concrete method call and its source

  Scenario: Borrow the first command when no settings file is supplied
    Given an isolated snippet project with distinct compilation commands
    When I asynchronously parse a snippet without selecting a settings file
    Then the first compilation command supplies its defines and header paths

  Scenario Outline: Parse C++ literals through the console engines
    Given an isolated snippet project with distinct compilation commands
    When I run a template snippet through the <engine> console engine
    Then the console reports the snippet member call

    Examples:
      | engine   |
      | compiled |
      | legacy   |

  Scenario: Parse a C++ literal through the native scripting service
    Given an isolated snippet project with distinct compilation commands
    When I analyze a template snippet through the native scripting service
    Then the native script reports the instantiated call

  Scenario: Analyze standalone C++ statements without options
    Given an isolated snippet project with distinct compilation commands
    When I parse standalone statements without compilation options
    Then their local variable is available for native matching
