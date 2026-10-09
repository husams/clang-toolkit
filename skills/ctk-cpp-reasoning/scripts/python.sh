#!/usr/bin/env bash
set -euo pipefail

ctk_skill_root="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
if [[ -n "${CTK_SDK_PROJECT:-}" ]]; then
    ctk_project="$CTK_SDK_PROJECT"
else
    ctk_project="${ctk_skill_root}/sdk-project"
fi

exec uv run --no-sync --project "$ctk_project" python "$@"
