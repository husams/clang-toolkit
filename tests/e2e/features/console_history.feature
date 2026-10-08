@e2e
Feature: Persistent interactive console history
  Scenario: Up and Down traverse persisted commands without losing the draft
    Given an isolated console history file
    When I submit commands and navigate history after restarting the prompt
    Then history returns commands newest first and restores the draft

  Scenario: Multiline command survives restart and history recall
    Given an isolated console history file
    When I save and recall a multiline command through fresh prompts
    Then history preserves the exact multiline command as one record

  Scenario: Ctrl+R searches and accepts a saved command
    Given an isolated console history file
    When I reverse-search history and accept the matching command
    Then the prompt submits the exact saved command

  Scenario: Clearing history removes cached and persisted recall
    Given an isolated console history file
    When I clear history and restart the prompt
    Then Up has no saved command to recall
