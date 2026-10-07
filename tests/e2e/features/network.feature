Feature: gRPC network client
  Scenario Outline: Version commands identify the client and running server
    Given a query server using <transport>
    When I request versions through the CLI and SDK
    Then the remote version matches the running binary and both revisions are printed

    Examples:
      | transport |
      | unix      |
      | tcp       |

  Scenario: Parse failures expose Clang diagnostics through the SDK and console
    Given a query server using unix
    And a C++ file with a missing project header
    When I parse the invalid source through the SDK and real console
    Then both report the missing header and its source location

  Scenario Outline: Compilation database commands supply and refresh per-file flags
    Given a query server using unix
    And a project with a compilation database selected by <selection>
    When I parse through the SDK and console and update its compilation command
    Then the database include paths and changed flags produce the expected ASTs

    Examples:
      | selection |
      | automatic |
      | explicit  |

  Scenario Outline: Native parse blocks inherit client compilation profiles without a default file
    Given a query server using <transport>
    And a C++ file controlled by a client compilation profile
    When I run native parse blocks through the SDKs and real console without a default file
    Then the client working directory and compiler flags select the profile function

    Examples:
      | transport |
      | unix      |
      | tcp       |

  Scenario Outline: Configured public SDK contexts own independent results
    Given a query server using <transport>
    And a C++ file containing multiple expression roots
    When I use configured synchronous and asynchronous result contexts
    Then context cleanup preserves children and invalidates closed aliases

    Examples:
      | transport |
      | unix      |
      | tcp       |

  Scenario Outline: Configured client receive limits constrain real RPC responses
    Given a query server using <transport>
    And a C++ file containing multiple expression roots
    When I parse with a configured 16-byte receive limit
    Then the configured client rejects the oversized response

    Examples:
      | transport |
      | unix      |
      | tcp       |

  Scenario: Real interactive console accepts scoped parse and match expressions
    Given a query server using unix
    And a C++ file containing multiple expression roots
    When I enter parse and match expressions through the real console
    Then the console prints both yielded literals and exits cleanly

  Scenario Outline: Parse and match values preserve earlier native bindings
    Given a query server using <transport>
    And a C++ file containing multiple expression roots
    When I parse and match independent tree and binding values
    Then every result remains selectable after continuations and tree release

    Examples:
      | transport |
      | unix      |
      | tcp       |

  Scenario Outline: Scoped console expressions yield reusable values
    Given a query server using <transport>
    And a C++ file containing multiple expression roots
    When I run the approved scoped expressions in the interactive runtime
    Then the yielded value survives lexical cleanup and failed assignments

    Examples:
      | transport |
      | unix      |
      | tcp       |

  Scenario Outline: Native script scopes retain yielded native results
    Given a query server using <transport>
    And a C++ file containing multiple expression roots
    When I evaluate scoped parse and match expressions in the native script
    Then native continuation uses all rows and keeps yielded results usable

    Examples:
      | transport |
      | unix      |
      | tcp       |

  Scenario Outline: Server script composes native queries and publishes atomically
    Given a query server using <transport>
    And a C++ file containing a cursor workflow
    When I compose native analyses in a server script and exhaust its step budget
    Then the script contains typed query values and no native cursor handles

    Examples:
      | transport |
      | unix      |
      | tcp       |

  Scenario Outline: Native call graph returns finite functions and typed calls
    Given a query server using <transport>
    And a C++ file containing a cursor workflow
    When I build the native call graph and enforce its node limit
    Then the call graph connects the functions with a typed call

    Examples:
      | transport |
      | unix      |
      | tcp       |

  Scenario Outline: CFG returns owned typed blocks and bounded overloads
    Given a query server using <transport>
    And a C++ file containing a cursor workflow
    When I build the function CFG and reject a limited result
    Then the graph contains typed statements and valid block edges

    Examples:
      | transport |
      | unix      |
      | tcp       |

  Scenario Outline: Standalone traversal returns a typed preorder tree
    Given a query server using <transport>
    And a C++ file containing a cursor workflow
    When I traverse the file and enforce a node limit
    Then traversal contains the typed literal and a valid parent structure

    Examples:
      | transport |
      | unix      |
      | tcp       |

  Scenario: Oversized cursor response does not commit a new revision
    Given a cursor server with a 128-byte response limit
    And a C++ file containing a cursor workflow
    When I request an oversized cursor replacement
    Then the oversized response leaves revision one available for replacement

  Scenario Outline: Query over the configured local transport
    Given a query server using <transport>
    And a C++ file containing a declaration
    When I run the declaration query
    Then the stream contains a match and successful completion

    Examples:
      | transport |
      | unix      |
      | tcp       |

  Scenario: Bidirectional query session half-closes after matching
    Given a query server using unix
    And a C++ file containing a declaration
    When I run the query through a bidirectional session
    Then the session stream contains a match and completion

  Scenario: Bidirectional session rejects a second query definition
    Given a query server using unix
    When I define two queries in one bidirectional session
    Then the session reports a command rejection

  Scenario: Bidirectional session can be cancelled
    Given a query server using unix
    When I cancel an active bidirectional session
    Then the session reports cancellation

  Scenario: A later limited file batch is rejected while accepted work completes
    Given a query server with a one-file limit
    And a C++ file containing a declaration
    When I match the first file and add a second file
    Then the second batch is rejected while the first file completes

  Scenario: Nested semantic values arrive as complete typed payloads
    Given a query server using unix
    And a C++ file containing a declaration
    When I run the declaration query
    Then the declaration contains a complete typed initializer and exact type

  Scenario Outline: Cursor continuation, revision checks, restart and close
    Given a query server using <transport>
    And a C++ file containing a cursor workflow
    When I continue, restart and close the matching cursor
    Then the cursor preserved its bindings on failure and advanced only successful revisions

    Examples:
      | transport |
      | unix      |
      | tcp       |

  Scenario Outline: Native dependency changes preserve pinned cursor snapshots
    Given a query server using unix
    When I replace a <kind> dependency after pinning its native snapshot
    Then new queries see nine and the pinned snapshot still sees seven

    Examples:
      | kind   |
      | header |
      | pch    |
      | module |
