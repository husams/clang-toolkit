"""Acceptance coverage for predicates shared by both prototype engines."""

from __future__ import annotations

import pytest

from clang_toolkit._generated.ast.v1 import common_pb2, node_pb2, semantic_pb2
from clang_toolkit._generated.match.v1 import match_result_pb2
from clang_toolkit.cli.app import dispatch_result
from clang_toolkit.cli.runtime.prototype import Context, compile_program, evaluate, parse, run_source
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
from clang_toolkit.cli.runtime.prototype.repl_language import parse as parse_repl
from clang_toolkit.cli.runtime.prototype.semantics import (
    CancelledError,
    EvaluationError,
    ExecutionLimitError,
)
from clang_toolkit.client import Client
from clang_toolkit.match_values import BindingSelection, MatchRow


@pytest.mark.parametrize("engine", ["tree", "compiled"])
@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('$record has a', True),
        ('$record has "a"', True),
        ('$record has ($key)', True),
        ('$record has absent', False),
        ('$record does not have absent', True),
        ('2 in $items', True),
        ('2 not in $items', False),
        ('1 in [1, {}]', True),
        ('1 in [true]', False),
        ('false in [0]', False),
        ('false in [0, false]', True),
        ('"" in ["", 0]', True),
        ('$null_value is defined', True),
        ('$null_value is not set', True),
        ('$false_value is defined and $false_value is set', True),
        ('$zero is set and $empty is set and $empty_string is set', True),
        ('$missing is not defined and $missing is not set', True),
        ('$missing is defined and $missing > 0', False),
        ('$record is defined', True),
    ],
)
def test_predicates_have_checked_shared_results(engine, source, expected):
    result = run_source(
        source,
        engine=engine,
        bindings={
            "record": {"a": None},
            "key": "a",
            "items": [1, 2, 3],
            "null_value": None,
            "false_value": False,
            "zero": 0,
            "empty": [],
            "empty_string": "",
        },
    )
    assert result.value is expected


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_predicates_obey_lazy_guards_shadowing_and_single_evaluation(engine):
    calls: list[str] = []
    source = (
        'let outer = "outer"\n'
        'let shadow = foreach outer in ["inner"] do $outer\n'
        'let guarded = $missing is defined and $missing > 0\n'
        'let safe = false and touch()\n'
        '[$shadow, $outer, $guarded, $safe]'
    )
    result = run_source(
        source,
        engine=engine,
        functions={"touch": lambda: calls.append("called")},
    )
    assert result.value == [["inner"], "outer", False, False]
    assert calls == []


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_predicate_operands_are_evaluated_once(engine):
    calls = {name: 0 for name in ("record", "key", "needle", "items", "node")}
    record_node = node_pb2.AstNode(cxx_record_decl=semantic_pb2.CXXRecordDecl())
    row = _semantic_row(record_node)

    def returns(name, value):
        def callback():
            calls[name] += 1
            return value

        return callback

    result = run_source(
        '[get_record() has (get_key()), get_needle() in get_items(), get_node() is CXXRecord]',
        engine=engine,
        functions={
            "get_record": returns("record", {"present": None}),
            "get_key": returns("key", "present"),
            "get_needle": returns("needle", 2),
            "get_items": returns("items", [1, 2, 3]),
            "get_node": returns("node", row.binding("record")),
        },
    )
    assert result.value == [True, True, True]
    assert calls == {name: 1 for name in calls}


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_binding_guard_avoids_lookup_and_host_effects(engine):
    class TrackingContext(Context):
        lookup_count = 0

        def lookup(self, name, node=None):
            self.lookup_count += 1
            return super().lookup(name, node)

    calls: list[str] = []
    program = parse("$missing is defined and touch()")
    context = TrackingContext(functions={"touch": lambda: calls.append("called")})
    result = evaluate(program, context) if engine == "tree" else compile_program(program)(context)
    assert result is False
    assert context.lookup_count == 0
    assert calls == []


def test_membership_operator_does_not_consume_native_match_target_in():
    program = parse_repl(
        'let matches = match callExpr().bind("call") in $rows.f\n'
        'let found = 2 in $items'
    )
    native_match, membership = program.children
    assert native_match.children[0].kind == "host"
    assert membership.children[0].kind == "predicate"
    assert membership.children[0].value == "in"


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_membership_stops_before_uncomparable_later_item(engine):
    assert run_source("1 in [1, {}]", engine=engine).value is True
    assert run_source(
        "$needle in $items",
        engine=engine,
        bindings={"needle": None, "items": [None, float("inf")]},
    ).value is True
    row = _semantic_row(node_pb2.AstNode(cxx_record_decl=semantic_pb2.CXXRecordDecl()))
    assert run_source(
        "$needle in $items",
        engine=engine,
        bindings={"needle": None, "items": [None, row.binding("record")]},
    ).value is True
    assert run_source(
        "$needle in $items",
        engine=engine,
        bindings={"needle": False, "items": [False, 1 << 70]},
    ).value is True
    with pytest.raises(EvaluationError, match="line 1"):
        run_source("2 in [1, {}]", engine=engine)
    with pytest.raises(EvaluationError, match="line 1"):
        run_source("2 not in [1, {}]", engine=engine)
    for needle in (None, False):
        for item in (float("inf"), float("nan"), 1 << 70):
            with pytest.raises(EvaluationError, match="line 1"):
                run_source(
                    "$needle in $items",
                    engine=engine,
                    bindings={"needle": needle, "items": [item]},
                )


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_membership_honors_step_limit_and_cancellation(engine):
    program = parse('$needle in $items')
    with pytest.raises(ExecutionLimitError, match="step limit"):
        context = Context({"needle": 9, "items": [1, 2, 3]}, max_steps=5)
        evaluate(program, context) if engine == "tree" else compile_program(program)(context)
    cancel_checks = 0

    def cancel_during_scan():
        nonlocal cancel_checks
        cancel_checks += 1
        return cancel_checks >= 5

    with pytest.raises(CancelledError, match="cancelled"):
        context = Context(
            {"needle": 9, "items": [1, 2, 3]},
            cancel_hook=cancel_during_scan,
        )
        evaluate(program, context) if engine == "tree" else compile_program(program)(context)
    assert cancel_checks == 5


@pytest.mark.parametrize("engine", ["tree", "compiled"])
@pytest.mark.parametrize(
    "source",
    [
        '$record["a"] has a',
        '2 in [2, {nested: 2}] and missing()',
        '$record is CXXRecord',
        '$record["a"] is set',
        '$record.field is set',
    ],
)
def test_invalid_predicate_operands_are_located(engine, source):
    with pytest.raises((EvaluationError, ValueError), match="line 1"):
        run_source(source, engine=engine, bindings={"record": {"a": 2}})


def _semantic_row(payload: node_pb2.AstNode) -> MatchRow:
    result = match_result_pb2.MatchResult()
    result.bindings["record"].CopyFrom(match_result_pb2.MatchBinding(node=payload))
    return MatchRow(result.SerializeToString(), None, 0)


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_node_kind_reads_exact_serialized_semantic_payload(engine):
    record = node_pb2.AstNode(cxx_record_decl=semantic_pb2.CXXRecordDecl())
    specialization = node_pb2.AstNode(
        class_template_specialization_decl=semantic_pb2.ClassTemplateSpecializationDecl()
    )
    row = _semantic_row(record)
    specialized_row = _semantic_row(specialization)
    assert run_source(
        '$row.record is CXXRecord and $row.record is CXXRecordDecl',
        engine=engine,
        bindings={"row": row},
    ).value is True
    assert run_source(
        '$row.record is not CXXRecord',
        engine=engine,
        bindings={"row": specialized_row},
    ).value is True
    assert run_source(
        '$row.record is ClassTemplateSpecializationDecl',
        engine=engine,
        bindings={"row": specialized_row},
    ).value is True


@pytest.mark.parametrize("engine", ["tree", "compiled"])
@pytest.mark.parametrize(
    ("state", "message"),
    [
        (common_pb2.FIELD_STATE_UNREQUESTED, "field was not requested"),
        (common_pb2.FIELD_STATE_UNAVAILABLE, "field is unavailable"),
    ],
)
def test_semantic_presence_keeps_availability_diagnostic(engine, state, message):
    result = match_result_pb2.MatchResult()
    binding = result.bindings["record"]
    binding.node.cxx_record_decl.CopyFrom(semantic_pb2.CXXRecordDecl())
    availability = binding.availability.add()
    availability.field_path = "cxx_record_decl.is_lambda"
    availability.state = state
    availability.reason = "fixture unavailable"
    row = MatchRow(result.SerializeToString(), None, 0)
    with pytest.raises(EvaluationError, match=message):
        run_source('$row.record has is_lambda', engine=engine, bindings={"row": row})
    with pytest.raises(EvaluationError, match=message):
        run_source('$row.record does not have is_lambda', engine=engine, bindings={"row": row})


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_semantic_presence_distinguishes_present_false_from_absent(engine):
    present_false = match_result_pb2.MatchBinding(
        node=node_pb2.AstNode(
            cxx_record_decl=semantic_pb2.CXXRecordDecl(is_lambda=False)
        )
    )
    absent = match_result_pb2.MatchBinding(
        node=node_pb2.AstNode(cxx_record_decl=semantic_pb2.CXXRecordDecl())
    )
    assert run_source(
        '$row.record has is_lambda',
        engine=engine,
        bindings={"row": _semantic_row(
            node_pb2.AstNode(cxx_record_decl=present_false.node.cxx_record_decl)
        )},
    ).value is True
    assert run_source(
        '$row.record does not have is_lambda',
        engine=engine,
        bindings={"row": _semantic_row(
            node_pb2.AstNode(cxx_record_decl=absent.node.cxx_record_decl)
        )},
    ).value is True


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_node_kind_diagnoses_missing_unsupported_and_unindexed_values(engine):
    empty_node = match_result_pb2.MatchBinding(node=node_pb2.AstNode())
    unsupported = match_result_pb2.MatchBinding(
        unsupported=node_pb2.UnsupportedValue(detail="fixture unsupported kind")
    )
    unindexed = BindingSelection("record", None)
    for value, message in (
        (empty_node, "no active payload"),
        (unsupported, "unsupported semantic payload"),
        (unindexed, "explicit row index"),
    ):
        with pytest.raises(EvaluationError, match=message):
            run_source('$node is CXXRecord', engine=engine, bindings={"node": value})


def test_compiled_predicates_do_not_dispatch_to_tree_evaluator(monkeypatch):
    record = node_pb2.AstNode(cxx_record_decl=semantic_pb2.CXXRecordDecl())
    program = parse(
        'let record = {a: null}; let has = $record has a; '
        'let lacks_key = $record does not have b; let member = 2 in [1, 2, {}]; '
        'let negated = 9 not in [1, 2]; let known = $node is CXXRecord; '
        'let wrong_kind = $node is not FunctionDecl; let defined = $node is defined; '
        'let absent_check = $node is not defined; let binding_set = $node is set; '
        'let unset = $nil_value is not set; '
        '[$has, $lacks_key, $member, $negated, $known, $wrong_kind, $defined, $absent_check, $binding_set, $unset]'
    )
    monkeypatch.setattr(
        "clang_toolkit.cli.runtime.prototype.semantics.eval_expr",
        lambda *_: (_ for _ in ()).throw(AssertionError("tree expression dispatch")),
    )
    monkeypatch.setattr(
        "clang_toolkit.cli.runtime.prototype.semantics.eval_statement",
        lambda *_: (_ for _ in ()).throw(AssertionError("tree statement dispatch")),
    )
    context = Context({"node": _semantic_row(record).binding("record"), "nil_value": None})
    assert compile_program(program)(context) == [True] * 7 + [False, True, True]


def test_prototype_help_documents_all_predicate_forms(tmp_path):
    runtime = PrototypeRuntime(Client(), script_engine="compiled", cwd=tmp_path, environment={})
    try:
        outcome = dispatch_result(runtime.client, "help predicates", runtime)
        assert outcome.success
        for form in (
            "$record has a",
            "$record does not have a",
            "2 in $items",
            "2 not in $items",
            "$node is CXXRecord",
            "$node is not CXXRecord",
            "$x is defined",
            "$x is not defined",
            "$x is set",
            "$x is not set",
        ):
            assert form in outcome.output
        assert outcome.markdown is not None and "| Test | Syntax |" in outcome.markdown
    finally:
        runtime.close()
        runtime.client.close()


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_unknown_node_kind_is_diagnosed(engine):
    record = node_pb2.AstNode(cxx_record_decl=semantic_pb2.CXXRecordDecl())
    row = _semantic_row(record)
    with pytest.raises(EvaluationError, match="unknown node kind"):
        run_source('$row.record is InventedDecl', engine=engine, bindings={"row": row})


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_repl_predicates_persist_across_submissions_and_fail_atomically(engine, tmp_path):
    runtime = PrototypeRuntime(Client(), script_engine=engine, cwd=tmp_path, environment={})
    try:
        first = dispatch_result(runtime.client, 'let record = {a: null}; let key = "a"', runtime)
        assert first.success
        second = dispatch_result(
            runtime.client,
            'let present = $record has ($key); let safe = $missing is defined and $missing > 0',
            runtime,
        )
        assert second.success, second.output
        assert runtime.bindings == {"record": {"a": None}, "key": "a", "present": True, "safe": False}
        failed = dispatch_result(runtime.client, "let broken = 2 in [1, {}]", runtime)
        assert not failed.success
        assert "line 1" in failed.output
        assert "broken" not in runtime.bindings
    finally:
        runtime.close()
        runtime.client.close()


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_repl_defined_and_set_use_environment_config_and_shadowing(engine, tmp_path):
    runtime = PrototypeRuntime(
        Client(),
        script_engine=engine,
        cwd=tmp_path,
        environment={"value": None},
    )
    runtime.config_vars["value"] = 0
    try:
        result = dispatch_result(
            runtime.client,
            'let env_available = $env is defined and $env is set\n'
            'let config_available = $config is defined and $config is set\n'
            'let shadowed = if true then { let env = null; $env is defined and $env is not set } else false\n'
            '[$env_available, $config_available, $shadowed]',
            runtime,
        )
        assert result.success, result.output
        assert runtime.bindings["env_available"] is True
        assert runtime.bindings["config_available"] is True
        assert runtime.bindings["shadowed"] is True
    finally:
        runtime.close()
        runtime.client.close()
