from __future__ import annotations

import pytest

from clang_toolkit.cli.runtime.prototype.__main__ import main


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_cli_runs_complete_value_expression_and_mutation(engine, capsys):
    source = "let total = 0; foreach item in [2,4,6] do $total += $item; print ($total > 10 ? 10 : 20)"
    assert main(["--source", source, "--engine", engine]) == 0
    assert capsys.readouterr().out.strip() == "10"


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_cli_skips_unregistered_host_call_in_unselected_branch(engine, capsys):
    assert main(["--source", "print (true ? 7 : never_called())", "--engine", engine]) == 0
    assert capsys.readouterr().out.strip() == "7"


def test_cli_exposes_actual_generated_loop_without_executing(capsys):
    source = "foreach item in [1,2] do never_called($item)"
    assert main(["--source", source, "--show-python"]) == 0
    output = capsys.readouterr().out
    assert "for " in output
    assert "never_called" in output
    assert "eval_statement" not in output and "eval_expr" not in output


def test_cli_reports_limits_and_invalid_syntax_without_traceback(capsys):
    assert main(["--source", "print 7", "--max-steps", "0"]) == 1
    error = capsys.readouterr().err
    assert "step limit" in error and "Traceback" not in error
    assert main(["--source", "let x = @"]) == 1
    assert "Traceback" not in capsys.readouterr().err
