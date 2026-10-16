Feature: Useful callgraphs from retained native inputs
  Scenario Outline: Filenames and retained inputs agree without reparsing
    Given an isolated callgraph server using <transport>
    When I inspect callgraphs from files trees handles and matched nodes
    Then exact graph selections preserve their native snapshot and static coverage

    Examples:
      | transport |
      | unix      |
      | tcp       |

  Scenario Outline: The compiled console runs the practical caller workflow
    Given an isolated callgraph server using <transport>
    When I run the practical retained callgraph console script
    Then the console returns shallow graph values and the selected caller edges

    Examples:
      | transport |
      | unix      |
      | tcp       |

  Scenario Outline: Unlimited depth reaches every callable in the selected component
    Given an isolated callgraph server using <transport>
    When I select all reachable calls from retained callable bindings
    Then unlimited callgraph depth crosses 32 hops and terminates on cycles

    Examples:
      | transport |
      | unix      |
      | tcp       |

  Scenario: Callgraph streams exceed the aggregate message limit
    Given an isolated callgraph server with small messages
    When I consume a callgraph larger than one message
    Then event bounds counts cancellation and completion remain explicit
