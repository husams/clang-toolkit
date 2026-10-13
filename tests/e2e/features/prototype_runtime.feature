Feature: Prototype runtime host bridge
  Scenario: Prototype status branches and skips an unselected host operation
    Given a prototype query server using unix
    When I run prototype status and lazy host calls through both engines
    Then both prototype engines report ready without opening a file

  Scenario: Prototype host match values support typed continuation
    Given a prototype query server using unix
    And a prototype C++ file with a caller and callee
    When I run prototype match continuation through both engines
    Then both prototype engines return the typed callee and clean native resources
