Feature: Retained local variable tracking
  Scenario Outline: Track the Page example through the native server and console
    Given an isolated variable flow server using <transport>
    When I analyze a retained variable after removing its source
    Then the converged report identifies the uninitialized read and dead assignment

    Examples:
      | transport |
      | unix      |
      | tcp       |
