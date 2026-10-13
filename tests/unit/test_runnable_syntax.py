from __future__ import annotations

import pytest

from clang_toolkit.cli.runtime.prototype.syntax import parse


@pytest.mark.parametrize("signature", ["ready()", "scale(value, factor)"])
def test_runnable_signature_has_dormant_body(signature):
    node = parse(f"let {signature} = {{ print 7 }}").children[0]
    assert node.kind == "runnable"
    assert node.children[0].kind == "block"
    assert node.children[0].children[0].kind == "print"


def test_bare_references_assignment_and_keys():
    nodes = parse("let value = 2; value += 1; let report = {value: value}").children
    assert nodes[1].children[0].kind == "ref"
    assert nodes[2].children[0].children[0].value == "value"
    assert nodes[2].children[0].children[0].children[0].kind == "ref"


def test_duplicate_parameters_fail_before_execution():
    with pytest.raises(ValueError, match="duplicate parameter"):
        parse("let f(value, value) = { value }")
