@e2e
Feature: Indexed project name completion
  Scenario: Select an indexed project from a real console independently of its working directory
    Given an indexed ctk-lab project for completion
    When I select ctk-lab after in using Tab in the actual console
    Then the scoped symbol search finds flow clamp and the menu shows its indexed path
