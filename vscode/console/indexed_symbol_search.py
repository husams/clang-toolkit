"""JSON-line bridge to the server's persistent project index."""
from __future__ import annotations

from dataclasses import replace
import json
import sys
from pathlib import Path
from typing import Any

_console_package = Path(__file__).parent
_workspace_package = Path(__file__).resolve().parents[2] / "python"
sys.path.insert(
    0,
    str(
        _workspace_package
        if (_workspace_package / "clang_toolkit").is_dir()
        else _console_package
    ),
)


def _symbol(symbol: Any, project: str, source_lines: dict[str, list[str]]) -> dict[str, Any]:
    file = str(symbol.file_path)
    line = int(symbol.line)
    lines = source_lines.get(file)
    if lines is None:
        try:
            lines = Path(file).read_text(errors="replace").splitlines()
        except OSError:
            lines = []
        source_lines[file] = lines
    result = {
        "id": f"{project}:{symbol.usr}:{file}:{line}:{symbol.column}",
        "name": symbol.qualified_name or symbol.name,
        "kind": symbol.kind,
        "file": file,
        "line": line,
        "column": max(1, int(symbol.column)),
        "excerpt": lines[line - 1].strip() if 0 < line <= len(lines) else "",
        "project": project,
    }
    translation_unit = str(getattr(symbol, "translation_unit", "") or "")
    if translation_unit:
        result["translationUnit"] = translation_unit
    return result


def _index_state(project: Any, stale: bool) -> dict[str, Any]:
    """Expose the fetched lifecycle and coverage counters to the VS Code view."""
    return {
        "root": project.project_root,
        "state": int(project.state),
        "indexed": int(project.translation_units_indexed),
        "total": int(project.translation_units_total),
        "completed": int(project.translation_units_completed),
        "skipped": int(project.translation_units_skipped),
        "failed": int(project.translation_units_failed),
        "stale": stale,
    }


def _page_integer(response: Any, field: str) -> int:
    value = getattr(response, field, None)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"Alias search returned an invalid {field}.")
    return value


def execute(request: dict[str, Any]) -> dict[str, Any]:
    from clang_toolkit.client import Client
    from clang_toolkit.cursors import CursorError

    client = Client(
        request.get("endpoint") or None,
        config_path=request.get("configPath") or None,
        compilation_database=request.get("compilationDatabase") or None,
    )
    client._resolved_config = replace(
        client._configuration(), rpc_timeout=max(1, request["timeoutMs"]) / 1000
    )
    try:
        projects = client.list_project_indexes().projects
        project_by_root = {item.project_root: item for item in projects}
        roots = sorted(project_by_root)
        if request["mode"] == "projects":
            return {"projects": roots, "results": [], "errors": [], "status": ""}
        if not roots:
            return {"projects": [], "results": [], "errors": [],
                    "status": "No indexed projects are available. Start a project index, then search again."}
        selected = request.get("project", "")
        if request["scope"] == "project":
            if not selected:
                directory = Path(request.get("directory", "")).resolve()
                candidates = []
                for root in roots:
                    try:
                        directory.relative_to(Path(root).resolve())
                        candidates.append(root)
                    except ValueError:
                        pass
                selected = max(candidates, key=len, default=roots[0])
            if selected not in roots:
                return {"projects": roots, "results": [], "errors": [],
                        "status": "Choose an indexed project before searching."}
            roots = [selected]
        kinds = set(request.get("kinds", []))
        if not kinds:
            return {
                "projects": roots,
                "results": [],
                "errors": [],
                "status": "Select at least one symbol kind.",
            }
        query = request["query"]
        enumerate_aliases = not query.strip() and kinds == {"aliases"}
        if not query.strip() and not enumerate_aliases:
            return {"projects": sorted({item.project_root for item in projects}),
                    "results": [], "errors": [], "status": "Enter a symbol name or prefix."}
        maximum = request["maximum"]
        results: list[dict[str, Any]] = []
        errors: list[str] = []
        sources: dict[str, list[str]] = {}
        any_coverage = False
        stale = False
        stale_by_root = {root: False for root in roots}
        truncated = False
        source_only = bool(request.get("sourceOnly", False))
        kind_by_category = {
            "variables": "variable", "classes": "class",
            "functions": "function", "aliases": "alias",
        }
        for root in roots:
            for category, kind in kind_by_category.items():
                if category not in kinds:
                    continue
                try:
                    offset = 0
                    expected_revision = 0
                    revision_pinned = False
                    seen_offsets: set[int] = set()
                    indexed_count: int | None = None
                    while True:
                        response = client.find_symbols(
                            root, "" if enumerate_aliases else query,
                            limit=1000 if enumerate_aliases else min(1000, maximum),
                            prefix=True if enumerate_aliases else not request["exact"], kind=kind,
                            unique_symbols=True, source_only=source_only,
                            offset=offset, expected_revision=expected_revision,
                        )
                        translation_units = int(response.translation_units_indexed)
                        page_stale = bool(response.stale)
                        if indexed_count is not None and translation_units != indexed_count:
                            raise ValueError("Alias search indexed coverage changed during enumeration.")
                        indexed_count = translation_units
                        any_coverage = any_coverage or translation_units > 0
                        stale = stale or page_stale
                        stale_by_root[root] = stale_by_root[root] or page_stale
                        results.extend(_symbol(item, root, sources) for item in response.symbols)
                        if not enumerate_aliases:
                            truncated = truncated or bool(response.truncated)
                            break
                        revision = _page_integer(response, "revision")
                        if not revision_pinned:
                            expected_revision = revision
                            revision_pinned = True
                        elif revision != expected_revision:
                            raise ValueError("Alias index revision changed during enumeration.")
                        next_offset = _page_integer(response, "next_offset")
                        if not bool(response.truncated):
                            if next_offset != 0:
                                raise ValueError("Alias search returned a nonzero next_offset on the final page.")
                            break
                        if next_offset <= offset or next_offset in seen_offsets:
                            raise ValueError("Alias search returned a repeated or non-advancing next_offset.")
                        if next_offset != offset + len(response.symbols):
                            raise ValueError("Alias search returned an invalid next_offset for the page.")
                        seen_offsets.add(offset)
                        offset = next_offset
                except CursorError as error:
                    errors.append(f"{root}: {error}")
                    if enumerate_aliases:
                        truncated = True
                except ValueError as error:
                    errors.append(f"{root}: {error}")
                    if enumerate_aliases:
                        truncated = True
        # The same header declaration can be returned through several TUs.
        # The key retains overload USRs and distinct definition locations.
        results = list({item["id"]: item for item in results}.values())
        results.sort(key=lambda item: (item["project"], item["file"], item["line"], item["column"]))
        if not enumerate_aliases and len(results) > maximum:
            truncated = True
            results = results[:maximum]
        status = ""
        if stale:
            status = "These results came from a stale index. Reindex the project to refresh them."
        if truncated and not enumerate_aliases:
            warning = "Results were truncated at the server limit. Narrow the name or search one project at a time."
            status = f"{status} {warning}".strip()
        elif errors and enumerate_aliases:
            status = f"{status} Alias enumeration is incomplete; see errors for the pages that failed.".strip()
        if not any_coverage and not errors:
            status = "This project index has no indexed translation units yet. Start or resume indexing, then search again."
        return {"projects": sorted({item.project_root for item in projects}),
                "results": results, "errors": errors, "status": status,
                "truncated": truncated,
                "indexStates": [
                    _index_state(project_by_root[root], stale_by_root[root])
                    for root in roots
                ]}
    finally:
        client.close()


if __name__ == "__main__":
    try:
        print(json.dumps(execute(json.loads(sys.stdin.readline()))), flush=True)
    except Exception as error:
        print(json.dumps({"error": str(error)}), flush=True)
        sys.exit(1)
