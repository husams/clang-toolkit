from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from dataclasses import dataclass

MODULE_PATH = Path(__file__).parents[1] / "console" / "indexed_symbol_search.py"
spec = importlib.util.spec_from_file_location("indexed_symbol_search", MODULE_PATH)
assert spec and spec.loader
search = importlib.util.module_from_spec(spec)
spec.loader.exec_module(search)


@dataclass(frozen=True)
class FakeConfig:
    rpc_timeout: float = 1.0


class FakeClient:
    roots = ["/projects/a", "/projects/b"]
    symbols = {
        "/projects/a": [
            SimpleNamespace(usr="fn", name="work", qualified_name="ns::work", kind="Function", file_path=__file__, line=1, column=1, translation_unit="/projects/a/main.cpp"),
            SimpleNamespace(usr="alias", name="Alias", qualified_name="ns::Alias", kind="TypeAlias", file_path=__file__, line=1, column=1, translation_unit="/projects/a/main.cpp"),
            SimpleNamespace(usr="alias", name="Alias", qualified_name="ns::Alias", kind="TypeAlias", file_path=__file__, line=1, column=1, translation_unit="/projects/a/other.cpp"),
        ],
        "/projects/b": [
            SimpleNamespace(usr="var", name="value", qualified_name="ns::value", kind="Var", file_path=__file__, line=1, column=1, translation_unit="/projects/b/main.cpp"),
        ],
    }
    calls: list[tuple[str, str, dict[str, object]]] = []

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.closed = False

    def _configuration(self) -> object:
        return FakeConfig()

    def list_project_indexes(self) -> object:
        states = {
            "/projects/a": (8, 7, 10, 9, 2, 0),
            "/projects/b": (5, 4, 4, 4, 0, 0),
        }
        return SimpleNamespace(projects=[
            SimpleNamespace(
                project_root=root,
                state=states.get(root, (1, 0, 0, 0, 0, 0))[0],
                translation_units_indexed=states.get(root, (1, 0, 0, 0, 0, 0))[1],
                translation_units_total=states.get(root, (1, 0, 0, 0, 0, 0))[2],
                translation_units_completed=states.get(root, (1, 0, 0, 0, 0, 0))[3],
                translation_units_skipped=states.get(root, (1, 0, 0, 0, 0, 0))[4],
                translation_units_failed=states.get(root, (1, 0, 0, 0, 0, 0))[5],
            )
            for root in self.roots
        ])

    def find_symbols(self, root: str, query: str, **kwargs: object) -> object:
        self.calls.append((root, query, kwargs))
        matches = {
            "alias": {"TypeAlias", "Typedef", "NamespaceAlias"},
            "function": {"Function", "CXXMethod", "CXXConstructor", "CXXDestructor"},
            "class": {"CXXRecord", "Record", "Enum"},
            "variable": {"Var", "Field", "Binding"},
        }[kwargs["kind"]]
        return SimpleNamespace(
            symbols=[item for item in self.symbols[root] if item.kind in matches],
            translation_units_indexed=2,
            truncated=False,
            stale=False,
        )

    def close(self) -> None:
        self.closed = True


def install_client(monkeypatch: object) -> None:
    client_module = types.ModuleType("clang_toolkit.client")
    client_module.Client = FakeClient
    cursor_module = types.ModuleType("clang_toolkit.cursors")
    cursor_module.CursorError = RuntimeError
    package = types.ModuleType("clang_toolkit")
    package.__path__ = []
    monkeypatch.setitem(sys.modules, "clang_toolkit", package)
    monkeypatch.setitem(sys.modules, "clang_toolkit.client", client_module)
    monkeypatch.setitem(sys.modules, "clang_toolkit.cursors", cursor_module)
    FakeClient.calls = []
    FakeClient.roots = ["/projects/a", "/projects/b"]


def request(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "mode": "search", "query": "ns::", "scope": "global", "project": "",
        "kinds": ["aliases", "functions", "variables", "classes"], "exact": False,
        "maximum": 100, "timeoutMs": 1000,
    }
    value.update(updates)
    return value


def test_global_search_filters_selected_kinds_and_keeps_translation_unit(monkeypatch: object) -> None:
    install_client(monkeypatch)
    response = search.execute(request(kinds=["aliases"]))
    assert [item["name"] for item in response["results"]] == ["ns::Alias"]
    assert response["results"][0]["translationUnit"] == "/projects/a/other.cpp"
    assert len(FakeClient.calls) == 2
    assert len(response["results"]) == 1
    assert all(call[2]["kind"] == "alias" and call[2]["unique_symbols"] is True for call in FakeClient.calls)
    assert all(call[2]["limit"] == 100 for call in FakeClient.calls)
    assert response["indexStates"] == [
        {"root": "/projects/a", "state": 8, "indexed": 7, "total": 10,
         "completed": 9, "skipped": 2, "failed": 0, "stale": False},
        {"root": "/projects/b", "state": 5, "indexed": 4, "total": 4,
         "completed": 4, "skipped": 0, "failed": 0, "stale": False},
    ]


def test_project_scope_uses_selected_project_and_reports_missing_index(monkeypatch: object) -> None:
    install_client(monkeypatch)
    response = search.execute(request(scope="project", project="/projects/b", kinds=["variables"]))
    assert [item["name"] for item in response["results"]] == ["ns::value"]
    assert [call[0] for call in FakeClient.calls] == ["/projects/b"]
    assert {call[2]["kind"] for call in FakeClient.calls} == {"variable"}

    FakeClient.roots = []
    empty = search.execute(request())
    assert empty["results"] == []
    assert "No indexed projects" in empty["status"]


def test_unselected_project_defaults_to_the_root_containing_the_request_directory(monkeypatch: object) -> None:
    install_client(monkeypatch)
    response = search.execute(
        request(scope="project", project="", directory="/projects/b/src", kinds=["variables"])
    )
    assert [item["name"] for item in response["results"]] == ["ns::value"]
    assert [call[0] for call in FakeClient.calls] == ["/projects/b"]


def test_all_selected_kinds_use_server_filters_and_stale_coverage_is_reported(monkeypatch: object) -> None:
    install_client(monkeypatch)
    response = search.execute(request(kinds=["variables", "classes", "functions", "aliases"]))
    assert {call[2]["kind"] for call in FakeClient.calls} == {
        "variable", "class", "function", "alias",
    }
    assert all(call[2]["unique_symbols"] is True for call in FakeClient.calls)

    monkeypatch.setattr(
        FakeClient,
        "find_symbols",
        lambda self, root, query, **kwargs: SimpleNamespace(
            symbols=[], translation_units_indexed=1, truncated=False, stale=True,
        ),
    )
    stale = search.execute(request(kinds=["aliases"]))
    assert "stale index" in stale["status"]
    assert [state["stale"] for state in stale["indexStates"]] == [True, True]


def test_index_states_include_only_searched_project_and_attribute_staleness(monkeypatch: object) -> None:
    install_client(monkeypatch)

    def find_symbols(self: FakeClient, root: str, query: str, **kwargs: object) -> object:
        return SimpleNamespace(
            symbols=[], translation_units_indexed=1, truncated=False,
            stale=root == "/projects/b",
        )

    monkeypatch.setattr(FakeClient, "find_symbols", find_symbols)
    response = search.execute(
        request(scope="project", project="/projects/b", kinds=["aliases"])
    )

    assert response["projects"] == ["/projects/a", "/projects/b"]
    assert response["indexStates"] == [
        {"root": "/projects/b", "state": 5, "indexed": 4, "total": 4,
         "completed": 4, "skipped": 0, "failed": 0, "stale": True},
    ]


def test_stale_status_keeps_the_truncation_warning(monkeypatch: object) -> None:
    install_client(monkeypatch)
    monkeypatch.setattr(
        FakeClient,
        "find_symbols",
        lambda self, root, query, **kwargs: SimpleNamespace(
            symbols=[], translation_units_indexed=1, truncated=True, stale=True,
        ),
    )
    response = search.execute(request(kinds=["aliases"]))
    assert response["truncated"] is True
    assert "stale index" in response["status"]
    assert "truncated" in response["status"]
