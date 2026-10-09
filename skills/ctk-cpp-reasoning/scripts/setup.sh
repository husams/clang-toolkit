#!/usr/bin/env bash
set -euo pipefail

ctk_source_root="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

if (( $# > 1 )); then
    printf 'Usage: %s [destination-skill-directory]\n' "${0##*/}" >&2
    exit 2
fi

ctk_target_arg="${1:-${HOME}/.codex/skills/ctk-cpp-reasoning}"

if [[ "$ctk_target_arg" == /* ]]; then
    ctk_target_path="$ctk_target_arg"
else
    ctk_target_path="$PWD/$ctk_target_arg"
fi
if ! command -v uv >/dev/null 2>&1; then
    printf 'Error: uv is required to set up the CTK reasoning skill. Install uv and run this script again.\n' >&2
    exit 1
fi

mkdir -p "$ctk_target_path"
ctk_target_root="$(cd -- "$ctk_target_path" && pwd -P)"

# Avoid copying a skill onto itself, while leaving unrelated target files alone.
if [[ "$ctk_source_root" != "$ctk_target_root" ]]; then
    for ctk_entry in SKILL.md agents references scripts sdk-project/pyproject.toml sdk-project/uv.lock sdk-project/wheels; do
        ctk_entry_path="${ctk_source_root}/${ctk_entry}"
        if [[ -f "$ctk_entry_path" ]]; then
            ctk_file="$ctk_entry_path"
            ctk_relative="$ctk_entry"
            ctk_parent="${ctk_target_root}/$(dirname "$ctk_relative")"
            mkdir -p "$ctk_parent"
            cp -p "$ctk_file" "$ctk_parent/"
        elif [[ -d "$ctk_entry_path" ]]; then
            while IFS= read -r -d '' ctk_file; do
                ctk_relative="${ctk_file#"$ctk_source_root"/}"
                ctk_parent="${ctk_target_root}/$(dirname "$ctk_relative")"
                mkdir -p "$ctk_parent"
                cp -p "$ctk_file" "$ctk_parent/"
            done < <(find "$ctk_entry_path" \( -path "$ctk_target_root" -o -type d \( -name .venv -o -name __pycache__ \) -o -type f -name '*.pyc' \) -prune -o -type f -print0)
        fi
    done
fi

ctk_project="${ctk_target_root}/sdk-project"
uv python install --no-bin 3.14
uv sync --frozen --project "$ctk_project" --python 3.14

# Check the installed public SDK surface and that typed matchers compose.
uv run --no-sync --project "$ctk_project" python - <<'PY'
from clang_toolkit import Client, Matcher
from clang_toolkit.matchers import functionDecl, hasName, isDefinition, unless, isImplicit

query = functionDecl(isDefinition(), hasName("example"), unless(isImplicit())).bind("fn")
assert isinstance(query, Matcher)
assert query.to_query()
assert callable(Client)
PY

printf 'CTK reasoning skill is ready at %s\n' "$ctk_target_root"
