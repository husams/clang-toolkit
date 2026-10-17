Feature: Stream CFG blocks from retained native trees
  Scenario Outline: CFG reuses parsed trees and exact function bindings
    Given an isolated CFG server using <transport>
    When I stream CFGs after removing the parsed source
    Then the retained trees and matches remain usable without reparsing

    Examples:
      | transport |
      | unix      |
      | tcp       |

  Scenario: CFG streams beyond the individual message limit
    Given a CFG server with small messages and many blocks
    When I stream a CFG larger than one message
    Then each CFG event fits and incomplete streams fail explicitly
