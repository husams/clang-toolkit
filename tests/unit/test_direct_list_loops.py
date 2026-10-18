from __future__ import annotations

import ast
from pathlib import Path

import pytest
from clang_toolkit.cli.runtime.prototype.semantics import Context
from clang_toolkit.cli.runtime.prototype.syntax import parse
from clang_toolkit.cli.runtime.prototype.tree import evaluate

DEFINITIONS = (
    (Path(__file__).resolve().parents[2] / "examples/recursive_lists.ctk")
    .read_text()
    .split("let xs =")[0]
)


@pytest.fixture(scope="module", params=["tree", "compiled"])
def runtime_env(request, tmp_path_factory):
    from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
    from clang_toolkit.client import Client

    client = Client()
    runtime = PrototypeRuntime(
        client,
        script_engine=request.param,
        environment={},
        cwd=tmp_path_factory.mktemp("direct-loops"),
    )
    try:
        yield client, runtime
    finally:
        runtime.close()
        client.close()


@pytest.fixture
def execute(runtime_env):
    _client, runtime = runtime_env
    session = runtime._prototype_session

    def run(source, context):
        context.source = session.source = source
        context.session = session
        context.host_evaluator = session.host
        context.statement_observer = session.observe
        program, executable = session.program(source)
        context.string_templates = program.value or {}
        runtime._prototype_context = context
        runtime._scopes = context._scopes
        try:
            return (
                executable(context)
                if executable is not None
                else evaluate(program, context)
            )
        finally:
            runtime._prototype_context = None
            runtime._scopes = [runtime.bindings]
            session.parts.clear()

    return run


@pytest.mark.parametrize(
    "target, expression, expected",
    [
        ("map_into", "map_list(range(1000), (x) x * 2)", list(range(0, 2000, 2))),
        (
            "filter_into",
            "filter_list(range(1000), (x) x % 2 == 0)",
            list(range(0, 1000, 2)),
        ),
        ("reverse_list", "reverse_list(range(1000))", list(range(999, -1, -1))),
    ],
)
def test_recognized_functions_run_without_continuation_objects(
    execute, monkeypatch, target, expression, expected
):
    from clang_toolkit.cli.runtime.prototype import list_recursion

    context = Context()
    execute(DEFINITIONS, context)
    function = context.lookup(target)
    direct = getattr(function, "direct_loop", None)
    assert direct is not None, (
        "recognized recursive list functions need direct Python loops"
    )
    source = direct.__ctk_source__
    assert any(
        isinstance(node, (ast.For, ast.While)) for node in ast.walk(ast.parse(source))
    )
    assert not any(
        isinstance(node, (ast.Yield, ast.YieldFrom))
        for node in ast.walk(ast.parse(source))
    )
    assert "_Request" not in source and "_Frame" not in source and "_leaf" not in source

    def forbidden(*args, **kwargs):
        pytest.fail("recognized function allocated a continuation")

    monkeypatch.setattr(list_recursion, "_Request", forbidden)
    monkeypatch.setattr(list_recursion, "_Frame", forbidden)
    assert execute(expression, context) == expected


def test_map_recognition_uses_structure_and_accepts_renamed_parameters(console):
    _client, runtime = console
    source = (
        DEFINITIONS.replace("map_into", "collect")
        .replace("out", "buffer")
        .replace("h : t", "first : rest")
        .replace("f(h)", "f(first)")
        .replace("(t, f,", "(rest, f,")
    )
    runtime._execute_library_source(source, Path("renamed.ctk"))
    assert runtime.bindings["collect"].direct_loop is not None


def test_standalone_property_calls_are_not_specialized():
    context = Context()
    evaluate(parse(DEFINITIONS), context)
    assert all(
        context.lookup(name).direct_loop is None
        for name in ("map_into", "filter_into", "reverse_list")
    )


@pytest.fixture
def console(runtime_env, tmp_path):
    client, runtime = runtime_env
    runtime.bindings.clear()
    runtime._execute_library_source(DEFINITIONS, tmp_path / "definitions.ctk")
    return client, runtime


@pytest.mark.parametrize(
    "target, expression, expected",
    [
        ("map_into", "map_list(xs, (x) x * 2)", list(range(0, 2000, 2))),
        ("filter_into", "filter_list(xs, (x) x % 2 == 0)", list(range(0, 1000, 2))),
        ("reverse_list", "reverse_list(xs)", list(range(999, -1, -1))),
    ],
)
def test_prepared_console_uses_direct_loop_without_continuations(
    console, monkeypatch, target, expression, expected
):
    from clang_toolkit.cli.app import dispatch_result
    from clang_toolkit.cli.runtime.prototype import list_recursion

    client, runtime = console
    runtime.bindings["xs"] = list(range(1000))
    assert runtime.bindings[target].direct_loop is not None

    def forbidden(*args, **kwargs):
        pytest.fail("console fast path allocated a continuation")

    monkeypatch.setattr(list_recursion, "_Request", forbidden)
    monkeypatch.setattr(list_recursion, "_Frame", forbidden)
    result = dispatch_result(client, "let answer = " + expression, runtime)
    assert result.success, result.output
    assert runtime.bindings["answer"] == expected
    assert runtime.bindings["xs"] == list(range(1000))


@pytest.mark.parametrize(
    "target, expression",
    [
        ("map_into", "map_list(xs, (x) x * 2)"),
        ("filter_into", "filter_list(xs, (x) x % 2 == 0)"),
        ("reverse_list", "reverse_list(xs)"),
    ],
)
def test_console_step_trace_and_every_budget_match_general_path(
    console, monkeypatch, target, expression
):
    from clang_toolkit.cli.app import dispatch_result

    client, runtime = console
    runtime.bindings["xs"] = [1, 2, 3]
    function = runtime.bindings[target]
    direct = function.direct_loop
    original_tick = Context.tick
    traces, contexts = [], []
    limit = 1000

    def tick(context, node=None):
        context.max_steps = limit
        contexts.append(context)
        traces.append(
            (
                getattr(node, "kind", None),
                str(getattr(node, "value", None)),
                getattr(node, "line", None),
                getattr(node, "column", None),
                context.consume_depth,
                context.call_depth,
                len(context.scopes),
            )
        )
        return original_tick(context, node)

    monkeypatch.setattr(Context, "tick", tick)
    observations = []
    for enabled in (True, False):
        object.__setattr__(function, "direct_loop", direct if enabled else None)
        traces.clear()
        result = dispatch_result(client, expression, runtime)
        assert result.success, result.output
        observations.append(list(traces))
    assert observations[0] == observations[1]
    total = len(observations[0])
    for limit in range(total + 2):
        outcomes = []
        for enabled in (True, False):
            object.__setattr__(function, "direct_loop", direct if enabled else None)
            result = dispatch_result(client, expression, runtime)
            context = contexts[-1]
            outcomes.append(
                (result.success, result.output, context.steps, context.current_location)
            )
            assert context.call_depth == context.consume_depth == 0
            assert context.scopes == (context.bindings,)
        assert outcomes[0] == outcomes[1], (limit, outcomes)


@pytest.mark.parametrize(
    "target, expression",
    [
        ("map_into", "map_into(xs, (x) touch(x), out)"),
        ("filter_into", "filter_into(xs, (x) touch(x) > 1, out)"),
        ("reverse_list", "reverse_list(xs)"),
    ],
)
def test_snapshot_order_and_shallow_identity_match_general_path(
    execute, target, expression
):
    outcomes = []
    for enabled in (True, False):
        nested = [1]
        source = [nested, [2], [3]]
        output = source if target == "map_into" else [nested]
        seen = []

        def touch(item, seen=seen, source=source):
            seen.append(item)
            if len(seen) == 1:
                source.clear()
                source.append([99])
            return item if target == "map_into" else item[0]

        context = Context(
            bindings={"xs": source, "out": output}, functions={"touch": touch}
        )
        execute(DEFINITIONS, context)
        if not enabled:
            object.__setattr__(context.lookup(target), "direct_loop", None)
        result = execute(expression, context)
        outcomes.append((result, source, seen, context.steps))
        assert (
            any(item is nested for item in result)
            if target != "filter_into"
            else result[0] is nested
        )
        assert context.call_depth == context.consume_depth == 0
        assert context.scopes == (context.bindings,)
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize(
    "target, expression",
    [
        ("map_into", "map_into(xs, (x) out, out)"),
        ("map_into", "map_list(xs, (x, y) x + y)"),
        ("map_into", "map_list(xs, (x) 1 / (x - 2))"),
        ("filter_into", "filter_list(xs, (x) x)"),
        ("filter_into", "filter_list(xs, (x) 1 / (x - 2) > 0)"),
    ],
)
def test_callback_and_cycle_errors_match_general_path(execute, target, expression):
    from clang_toolkit.cli.runtime.prototype.semantics import PrototypeError

    outcomes = []
    for enabled in (True, False):
        context = Context(bindings={"xs": [1, 2, 3], "out": []})
        execute(DEFINITIONS, context)
        if not enabled:
            object.__setattr__(context.lookup(target), "direct_loop", None)
        with pytest.raises(PrototypeError) as caught:
            execute(expression, context)
        outcomes.append(
            (
                type(caught.value),
                str(caught.value),
                context.bindings["out"],
                context.steps,
            )
        )
        assert context.call_depth == context.consume_depth == 0
        assert context.scopes == (context.bindings,)
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize("size, maximum", [(0, 0), (1, 0), (3, 2), (3, 3), (4, 3)])
def test_reverse_pending_work_limit_matches_general_path(execute, size, maximum):
    from clang_toolkit.cli.runtime.prototype.semantics import PrototypeError

    outcomes = []
    for enabled in (True, False):
        context = Context(bindings={"xs": list(range(size))})
        execute(DEFINITIONS, context)
        context.max_items = maximum
        if not enabled:
            object.__setattr__(context.lookup("reverse_list"), "direct_loop", None)
        try:
            result = execute("reverse_list(xs)", context)
            outcome = ("ok", result)
        except PrototypeError as error:
            outcome = (type(error), str(error))
        outcomes.append((outcome, context.steps, context.current_location))
        assert context.call_depth == context.consume_depth == 0
        assert context.scopes == (context.bindings,)
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize(
    "target, expression",
    [
        ("map_into", "map_list(xs, (x) x * 2)"),
        ("filter_into", "filter_list(xs, (x) x > 1)"),
        ("reverse_list", "reverse_list(xs)"),
    ],
)
def test_event_cancellation_at_each_tick_matches_general_path(
    execute, monkeypatch, target, expression
):
    from threading import Event

    from clang_toolkit.cli.runtime.prototype.semantics import PrototypeError

    original_tick = Context.tick
    event = Event()
    context = Context(bindings={"xs": [1, 2, 3]})
    execute(DEFINITIONS, context)
    context.cancel_hook = event.is_set
    function = context.lookup(target)
    direct = function.direct_loop
    for cancel_at in range(1, 90):
        outcomes = []
        for enabled in (True, False):
            event.clear()
            context.steps = 0
            object.__setattr__(function, "direct_loop", direct if enabled else None)

            def tick(ctx, node=None, cancel_at=cancel_at):
                if ctx is context and ctx.steps == cancel_at:
                    event.set()
                return original_tick(ctx, node)

            monkeypatch.setattr(Context, "tick", tick)
            try:
                result = execute(expression, context)
                outcome = ("ok", result)
            except PrototypeError as error:
                outcome = (type(error), str(error))
            outcomes.append((outcome, context.steps, context.current_location))
            assert context.call_depth == context.consume_depth == 0
            assert context.scopes == (context.bindings,)
            monkeypatch.setattr(Context, "tick", original_tick)
        assert outcomes[0] == outcomes[1], (cancel_at, outcomes)


@pytest.mark.parametrize(
    "case",
    [
        "python_callback",
        "input_subclass",
        "output_subclass",
        "cancel_hook",
        "host_override",
    ],
)
def test_runtime_guards_retain_general_execution(console, monkeypatch, case):
    from clang_toolkit.cli.app import dispatch_result
    from clang_toolkit.cli.runtime.prototype.list_recursion import RecursiveListProgram

    client, runtime = console

    class ListSubclass(list):
        pass

    runtime.bindings["xs"] = (
        ListSubclass([1, 2]) if case == "input_subclass" else [1, 2]
    )
    runtime.bindings["out"] = ListSubclass() if case == "output_subclass" else []
    runtime.bindings["host_callback"] = lambda x: x * 2
    calls = []
    original = RecursiveListProgram.run

    def run(program, context, arguments, owner, node):
        if owner.name == "map_into":
            calls.append(owner.name)
        return original(program, context, arguments, owner, node)

    monkeypatch.setattr(RecursiveListProgram, "run", run)
    original_tick = Context.tick

    def tick(context, node=None):
        if case == "cancel_hook":
            context.cancel_hook = lambda: False
        elif case == "host_override":
            context.host_evaluator = lambda ctx, leaf: runtime._prototype_session.host(
                ctx, leaf
            )
        return original_tick(context, node)

    monkeypatch.setattr(Context, "tick", tick)
    callback = "host_callback" if case == "python_callback" else "(x) x * 2"
    result = dispatch_result(
        client, f"let answer = map_into(xs, {callback}, out)", runtime
    )
    assert result.success, result.output
    assert runtime.bindings["answer"] == [2, 4]
    assert calls == ["map_into"]


@pytest.mark.parametrize(
    "target,expression",
    [
        ("map_into", "map_list(xs, (x) x)"),
        ("filter_into", "filter_list(xs, (x) x > 0)"),
        ("reverse_list", "reverse_list(xs)"),
    ],
)
@pytest.mark.parametrize(
    "which_tick, mutation", [(1, "change"), (2, "change"), (1, "clear"), (2, "clear")]
)
def test_snapshot_follows_first_clause_matching(
    console, monkeypatch, target, expression, which_tick, mutation
):
    from clang_toolkit.cli.app import dispatch_result

    client, runtime = console
    function = runtime.bindings[target]
    direct = function.direct_loop
    original_tick = Context.tick
    outcomes = []
    for enabled in (True, False):
        runtime.bindings["xs"] = [1, 2, 3]
        seen = 0
        object.__setattr__(function, "direct_loop", direct if enabled else None)

        def tick(context, node=None):
            nonlocal seen
            if node is function.body:
                seen += 1
                if seen == which_tick:
                    if mutation == "clear":
                        runtime.bindings["xs"].clear()
                    else:
                        runtime.bindings["xs"][1] = 99
            return original_tick(context, node)

        monkeypatch.setattr(Context, "tick", tick)
        result = dispatch_result(client, "let answer = " + expression, runtime)
        outcomes.append((result.success, result.output, runtime.bindings.get("answer")))
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize(
    "target, expression",
    [
        ("map_into", "map_into(xs, (x) { switch(); x }, out)"),
        ("filter_into", "filter_into(xs, (x) { switch(); true }, out)"),
    ],
)
@pytest.mark.parametrize("mode", ["raise", "return", "rebind"])
def test_callbacks_can_replace_host_evaluation_mid_loop(
    execute, target, expression, mode
):
    from clang_toolkit.cli.runtime.prototype.semantics import PrototypeError

    outcomes = []
    for enabled in (True, False):
        context = Context(bindings={"xs": [1, 2, 3], "out": []})
        seen = []

        def replacement(ctx, node, seen=seen):
            seen.append("host")
            if mode == "raise":
                raise PrototypeError("switched host")
            if mode == "rebind":
                ctx.assign_binding("out", [42], node)
            return 99

        def switch(context=context, seen=seen, replacement=replacement):
            seen.append("callback")
            context.host_evaluator = replacement

        context.functions["switch"] = switch
        execute(DEFINITIONS, context)
        if not enabled:
            object.__setattr__(context.lookup(target), "direct_loop", None)
        try:
            value = execute(expression, context)
            outcome = ("ok", value)
        except PrototypeError as error:
            outcome = (type(error), str(error))
        outcomes.append((outcome, context.bindings["out"], seen, context.steps))
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize("error_type", [ValueError, IndexError, KeyError, RuntimeError])
@pytest.mark.parametrize(
    "target,expression",
    [
        ("map_into", "map_list(xs, (x) x)"),
        ("filter_into", "filter_list(xs, (x) true)"),
        ("reverse_list", "reverse_list(xs)"),
    ],
)
def test_nested_collection_errors_keep_console_diagnostics(
    execute, error_type, target, expression
):
    from clang_toolkit.cli.runtime.prototype.semantics import PrototypeError

    class BrokenList(list):
        def __iter__(self):
            raise error_type("nested iterator failed")

    outcomes = []
    for enabled in (True, False):
        context = Context(bindings={"xs": [BrokenList([1])]})
        execute(DEFINITIONS, context)
        if not enabled:
            object.__setattr__(context.lookup(target), "direct_loop", None)
        with pytest.raises(PrototypeError) as caught:
            execute(expression, context)
        outcomes.append((type(caught.value), str(caught.value), context.steps))
        assert context.call_depth == context.consume_depth == 0
        assert context.scopes == (context.bindings,)
    assert outcomes[0] == outcomes[1]
