Feature: Read semantic match fields in the console
  Scenario: Field extraction preserves native selection and result iteration
    Given a private native server and functions for field inspection
    When I extract names and continue matching through the real console
    Then the console prints function names and both continued literal values

  Scenario: Missing fields preserve earlier assignments
    Given a private native server and functions for field inspection
    When I read an inactive payload after assigning a previous value
    Then the console explains the unavailable field and preserves the previous value
