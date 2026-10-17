from __future__ import annotations

import pytest

from clang_toolkit.cli.runtime.prototype.semantics import Context, PrototypeError

from clang_toolkit.cli.runtime.prototype.compiler import compile_program
from clang_toolkit.cli.runtime.prototype.syntax import parse
from clang_toolkit.cli.runtime.prototype.repl_language import parse as parse_repl
from clang_toolkit.cli.runtime.prototype.tree import evaluate


@pytest.fixture(
    params=[
        (parse, "tree"),
        (parse, "compiled"),
        (parse_repl, "tree"),
        (parse_repl, "compiled"),
    ]
)
def execute(request):
    parser, engine = request.param

    def run(source, context=None):
        context = context or Context()
        context.source = source
        program = parser(source)
        return (
            evaluate(program, context)
            if engine == "tree"
            else compile_program(program)(context)
        )

    return run


MAP = "let map_list = { ([], f) []; (h : t, f) flatten([[f(h)], map_list(t, f)]) }; "
FILTER = "let filter_list = { ([], keep) []; (h : t, keep) if keep(h) then flatten([[h], filter_list(t, keep)]) else filter_list(t, keep) }; "
REVERSE = "let reverse_list = { ([]) []; (h : t) flatten([reverse_list(t), [h]]) }; "


@pytest.mark.parametrize(
    "definition, expression, expected",
    [
        (MAP, "map_list(range(150), (x) x * 2)", list(range(0, 300, 2))),
        (FILTER, "filter_list(range(150), (x) x % 2 == 0)", list(range(0, 150, 2))),
        (REVERSE, "reverse_list(range(150))", list(range(149, -1, -1))),
    ],
)
def test_recursive_list_operations_exceed_python_call_limit(
    execute, definition, expression, expected
):
    assert execute(definition + expression) == expected


def test_tail_calls_and_indexed_tails_handle_large_lists(execute):
    source = "let walk = { ([], n) n; (h : t, n) walk(t, n + h) }; walk(range(5000), 0)"
    assert execute(source) == 12497500


def test_general_non_tail_numeric_expressions_use_continuations(execute):
    assert (
        execute(
            "let twice = { ([]) 0; (h : t) h * 2 + twice(t) }; twice(range(5000))",
            Context(max_steps=200000),
        )
        == 24995000
    )


def test_callbacks_keep_order_and_snapshot_input_before_mutation(execute):
    values = [1, 2, 3]
    seen = []

    def change(value):
        seen.append(value)
        values[1] = 99
        return value * 10

    context = Context(functions={"change": change})
    context.define("values", values)
    assert execute(MAP + "map_list(values, change)", context) == [10, 20, 30]
    assert seen == [1, 2, 3]
    assert values == [1, 99, 3]


def test_returned_tails_are_mutable_independent_shallow_lists(execute):
    shared = [7]
    values = [0, shared, 2]
    context = Context(bindings={"values": values})
    result = execute("let drop_one = { ([]) []; (h : t) t }; drop_one(values)", context)
    assert type(result) is list and result[0] is shared
    result[1] = 99
    shared[0] = 8
    assert values == [0, [8], 2]


def test_escaping_tail_capture_has_original_list_semantics(execute):
    source = "let make = { ([]) () []; (h : t) () t }; let xs = [1, 2, 3]; let get = make(xs); xs[1] = 99; get()"
    assert execute(source) == [2, 3]


def test_non_tail_calls_keep_left_to_right_argument_order(execute):
    effects = []
    context = Context(functions={"mark": lambda n: effects.append(n) or n})
    source = "let walk = { ([]) 0; (h : t) mark(h) + walk(t) + mark(0 - h) }; walk([1, 2, 3])"
    assert execute(source, context) == 0
    assert effects == [1, 2, 3, -3, -2, -1]


def test_general_recursion_preserves_limits_and_restores_scopes(execute):
    context = Context(max_steps=80)
    with pytest.raises(PrototypeError, match="step limit"):
        execute(MAP + "map_list(range(20), (x) x)", context)
    assert context.call_depth == 0 and context.scopes == (context.bindings,)
    with pytest.raises(PrototypeError, match="zero"):
        execute("let bad = { ([]) 0; (h : t) bad(t) + 1 / h }; bad([1, 0, 2])")


def test_cancellation_restores_continuation_scopes(execute):
    context = Context()
    context.cancel_hook = lambda: context.steps > 400
    with pytest.raises(PrototypeError, match="cancelled"):
        execute(MAP + "map_list(range(150), (x) x)", context)
    assert context.call_depth == 0 and context.scopes == (context.bindings,)
    assert context.consume_depth == 0
    context.cancel_hook = None
    assert execute("1 + 2", context) == 3


def test_same_function_alias_keeps_original_self(execute):
    source = (
        MAP + "let old = map_list; let map_list = (xs, f) []; old(range(150), (x) x)"
    )
    assert execute(source) == list(range(150))


@pytest.mark.parametrize(
    "body",
    [
        "let f(xs) = 99; f(t)",
        "f = (xs) 99; f(t)",
    ],
)
def test_local_self_rebinding_preserves_ordinary_lookup(execute, body):
    assert execute("let f = { ([]) 0; (h : t) { " + body + " } }; f([1])") == 99


def test_internal_tails_do_not_materialize_per_recursive_call(execute, monkeypatch):
    from clang_toolkit.cli.runtime.prototype.list_recursion import _Cursor

    copies = []
    original = _Cursor.materialize

    def counted(self):
        copies.append(len(self))
        return original(self)

    monkeypatch.setattr(_Cursor, "materialize", counted)
    assert (
        execute(
            "let walk = { ([], n) n; (h : t, n) walk(t, n + h) }; walk(range(5000), 0)"
        )
        == 12497500
    )
    assert copies == []


def test_tail_accumulator_mutation_uses_one_backing_snapshot(execute, monkeypatch):
    from clang_toolkit.cli.runtime.prototype.list_recursion import _Arena, _Cursor

    snapshots, copies = [], []
    freeze, materialize = _Arena.freeze, _Cursor.materialize

    def frozen(self):
        if self.public:
            snapshots.append(len(self.public))
        return freeze(self)

    def copied(self):
        copies.append(len(self))
        return materialize(self)

    monkeypatch.setattr(_Arena, "freeze", frozen)
    monkeypatch.setattr(_Cursor, "materialize", copied)
    context = Context(functions={"append": lambda out, h: out.append(h)})
    source = "let into = { ([], out) out; (h : t, out) { append(out, h); into(t, out) } }; into(range(1000), [])"
    assert execute(source, context) == list(range(1000))
    assert len(snapshots) == 1 and copies == []


def test_compiled_recursion_never_interprets_body_nodes(execute, monkeypatch):
    from clang_toolkit.cli.runtime.prototype.compiler import compile_program
    from clang_toolkit.cli.runtime.prototype.syntax import parse
    from clang_toolkit.cli.runtime.prototype import semantics

    compiled = compile_program(parse(MAP + "map_list(range(150), (x) x * 2)"))
    monkeypatch.setattr(
        semantics,
        "eval_statement",
        lambda *_a, **_k: pytest.fail("body interpretation"),
    )
    assert compiled(Context()) == list(range(0, 300, 2))


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_custom_observers_keep_real_lists_and_original_frame_scopes(engine):
    from dataclasses import replace
    from clang_toolkit.cli.runtime.prototype.syntax import Node

    def prepared(node):
        result = replace(
            node, children=tuple(prepared(child) for child in node.children)
        )
        if result.kind in {"block", "program"}:
            result = replace(
                result,
                children=tuple(
                    Node("observe", children=(child,)) for child in result.children
                ),
            )
        return result

    values, seen = [1, 2, 3], []

    def observer(context, node, value):
        if node.kind == "ref" and node.value == "h":
            assert type(context.lookup("t")) is list
            values[1] = 99
        if node.kind == "call" and node.value == "f":
            seen.append(context.lookup("h") if context.lookup_scope("h") else None)

    context = Context(bindings={"values": values}, statement_observer=observer)
    program = prepared(parse("let f = { ([]) 0; (h : t) { h; h + f(t) } }; f(values)"))
    result = (
        evaluate(program, context)
        if engine == "tree"
        else compile_program(program)(context)
    )
    assert result == 6
    assert seen == [None]
    seen.clear()
    context = Context(statement_observer=observer)
    program = prepared(parse("let f = { ([]) 0; (h : t) f(t) }; f([1, 2, 3])"))
    result = (
        evaluate(program, context)
        if engine == "tree"
        else compile_program(program)(context)
    )
    assert result == 0 and seen == [3, 2, 1, None]


def test_preflight_is_once_and_cannot_mutate_an_uncopied_tail(execute):
    import inspect

    values, events = [1, 2, 3], []

    class Touch:
        @property
        def __signature__(self):
            events.append("signature")
            values[1] = 99
            return inspect.Signature(
                [inspect.Parameter("value", inspect.Parameter.POSITIONAL_ONLY)]
            )

        def __call__(self, value):
            events.append("call")
            return value

    context = Context(bindings={"values": values}, functions={"touch": Touch()})
    source = "let f = { ([]) 0; (h : t) h + touch(f(t)) }; f(values)"
    assert execute(source, context) == 6
    assert events == ["signature"] * 3 + ["call"] * 3


def test_dynamic_self_rebinding_dispatches_the_selected_callable(execute):
    context = Context()

    def rebind():
        context._scopes[-1]["f"] = lambda xs: 99 if type(xs) is list else -1

    context.functions["rebind"] = rebind
    assert (
        execute("let f = { ([]) 0; (h : t) { rebind(); f(t) } }; f([1, 2])", context)
        == 99
    )


@pytest.mark.parametrize("engine", ["tree", "compiled"])
@pytest.mark.parametrize(
    "definition, name, expression",
    [
        (MAP, "map_list", "map_list([1, 2, 3], (x) x * 2)"),
        (FILTER, "filter_list", "filter_list([1, 2, 3], (x) x % 2 == 0)"),
        (REVERSE, "reverse_list", "reverse_list([1, 2, 3])"),
        (
            "let walk = { ([]) 0; (h : t) { let n = walk(t); n + h } }; ",
            "walk",
            "walk([1, 2, 3])",
        ),
    ],
)
def test_generated_steps_match_ordinary_execution_in_prepared_console(
    engine, definition, name, expression
):
    from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
    from clang_toolkit.client import Client

    client = Client()
    runtime = PrototypeRuntime(client, script_engine=engine, environment={})
    try:
        source = definition + f"toggle({name}); " + expression
        program, compiled = runtime._prototype_session.program(source)
        steps = []
        for enabled in (True, False):

            def toggle(function):
                if not enabled:
                    object.__setattr__(function, "recursion", None)

            context = Context(functions={"toggle": toggle})
            result = (
                evaluate(program, context) if engine == "tree" else compiled(context)
            )
            assert result is not None
            steps.append(context.steps)
        assert steps[0] == steps[1]
    finally:
        runtime.close()
        client.close()


@pytest.mark.parametrize("operation", ["length", "index", "slice"])
def test_pattern_hooks_cannot_mutate_previously_bound_tails(execute, operation):
    values = [1, 2, 3]
    lengths = 0

    class Hooks(list):
        def __len__(self):
            nonlocal lengths
            lengths += 1
            if operation == "length" and lengths == 2:
                values[1] = 99
            return super().__len__()

        def __getitem__(self, index):
            if operation == ("slice" if isinstance(index, slice) else "index"):
                values[1] = 99
            return super().__getitem__(index)

    pattern = "other : rest" if operation == "slice" else "[other]"
    source = (
        "let f = { ([], _) 0; (h : t, " + pattern + ") h + f(t, hooks) }; "
        "f(values, hooks)"
    )
    context = Context(bindings={"values": values, "hooks": Hooks([7])})
    assert execute(source, context) == 6
    assert values == [1, 99, 3]
