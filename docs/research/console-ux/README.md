# Console experience research

Proposal: [editable Page](https://chatgpt.com/space/page_bf6289c8e8a48191a3c5b4bf61e98f8e).

The wiki bundle contains the research page, eight immutable Markdown source snapshots, and a patch for the research-specific index/log updates. It is staged here to honor the requirement that all work remain in a Git worktree. The canonical wiki is not a Git repository and is unchanged. wiki-catalog.patch records only the proposed catalog/log additions; Local copies of the personal wiki index and log remain outside the merged documentation.

The research baseline is ed20acf on codex/console-ux-exploration. The subsequent [CTK console workspace](../../console-workspace.md) adds the optional workspace to the console. probe_layout.py remains the earlier isolated feasibility experiment with prompt_toolkit 3.0.53; workspace tests exercise the actual application and native server through a real terminal.
