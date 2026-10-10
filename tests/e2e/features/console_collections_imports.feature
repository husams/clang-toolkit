Feature: Console collections and local libraries
  Scenario: Manipulate dictionaries and lists through a console batch
    Given a private server and a collection library fixture
    When I run the collection operations through the CLI
    Then the collection results preserve the requested values

  Scenario: Import matcher libraries relative to a script file
    Given a private server and a collection library fixture
    When I run a script importing nested matcher libraries
    Then the imported matcher and variables work against native results

  Scenario: Print native UTF-8 string literal bytes as text
    Given a private server and a collection library fixture
    When I print a native UTF-8 string literal through the CLI
    Then the console displays the decoded text

  Scenario: Discover keys of a retained matched value
    Given a private server and a collection library fixture
    When I read keys from the second retained root value
    Then the keys list the readable semantic properties

  Scenario: Save a binding and its semantic fields as detached snapshots
    Given a private server and a collection library fixture
    When I export a retained binding and its semantic fields
    Then the snapshots preserve the selected data and native matching continues

  Scenario: Display an indexed class binding without a value suffix
    Given a private server and a collection library fixture
    When I evaluate a class binding directly in the CLI
    Then the binding displays its semantic data and remains a native match root

  Scenario: Export AST properties without binding bookkeeping
    Given a private server and a collection library fixture
    When I save a class binding as JSON YAML and protobuf
    Then the text exports contain AST properties and protobuf retains availability

  Scenario: Execute multiline foreach statement blocks over matched rows
    Given a private server and a collection library fixture
    When I run multiline foreach blocks over retained matches
    Then foreach prints each name once and restores the outer iterator

  Scenario: Submit a foreach block by closing its brace in the prompt
    Given a private server and a collection library fixture
    When I enter a foreach statement block with individual Enter presses
    Then the closing brace submits the complete native iteration
