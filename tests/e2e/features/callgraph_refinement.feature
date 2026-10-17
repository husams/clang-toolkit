Feature: Useful callgraphs from retained native inputs
  Scenario Outline: Console boundaries retain user headers alongside stdexcept
    Given an isolated callgraph server using unix
    When I run the header boundary console example with <engine>
    Then the console excludes standard library and custom namespace nodes

    Examples:
      | engine   |
      | tree     |
      | compiled |

  Scenario Outline: Callable boundaries exclude system headers and custom matches
    Given an isolated callgraph server using <transport>
    When I filter system headers and custom callable boundaries from retained inputs
    Then filtered callgraphs keep user headers and stop at excluded callables

    Examples:
      | transport |
      | unix      |
      | tcp       |

  Scenario Outline: System root call sites are excluded while user headers remain
    Given an isolated callgraph server using <transport>
    When I exclude system root call sites from filename parsed and matched inputs
    Then system root facts are absent and user header calls keep their snapshot

    Examples:
      | transport |
      | unix      |
      | tcp       |

  Scenario Outline: Node limits are configurable and explicitly unlimited
    Given a callgraph server with node budget <budget> using <transport>
    When I override callgraph node budgets through filename tree and matched inputs
    Then node budgets retain complete graphs and snapshot ownership

    Examples:
      | transport | budget |
      | unix      | 1      |
      | tcp       | 1      |
      | unix      | 0      |
      | tcp       | 0      |

  Scenario Outline: Header builtin declarations remain ordered for retained inputs
    Given an isolated callgraph server using <transport>
    When I inspect a header va_list callable through retained graph inputs
    Then full-scope callgraphs preserve the header callable

    Examples:
      | transport |
      | unix      |
      | tcp       |

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
