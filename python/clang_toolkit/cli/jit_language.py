"""LLVM IR lowering for standalone CTK language constructs."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from .runtime.prototype.patterns import ConsPattern, ListPattern
from .runtime.prototype.syntax import Node


def unsupported(node: Node, message: str) -> ValueError:
    return ValueError(f"line {node.line}, column {node.column}: {message}")


class LanguageIR:
    def __init__(
        self,
        string: Callable[[str], str],
        constant: Callable[[str], str],
        host: Callable[[LanguageIR, Node], str],
    ) -> None:
        self.string = string
        self.constant = constant
        self.host = host
        self.declarations: dict[str, str] = {}
        self.lines: list[str] = []
        self.block = "entry"
        self.failure = "error"
        self.functions: list[str] = []
        self.serial = 0
        self.scope_depth = 0
        self.loops: list[tuple[str, str, int, int, int]] = []
        self.consume_depth = 0
        self.return_type = "i32"
        self.match_origin: tuple[int, int] | None = None
        self.cleanups: list[tuple[Node, int, str]] = []

    def fresh(self, prefix: str) -> str:
        self.serial += 1
        return f"{prefix}.{self.serial}"

    def emit(self, instruction: str) -> None:
        self.lines.append(f"  {instruction}")

    def label(self, name: str) -> None:
        self.lines.append(f"{name}:")
        self.block = name

    def guard(self, test: str) -> None:
        next_block = self.fresh("ok")
        self.emit(f"br i1 {test}, label %{next_block}, label %{self.failure}")
        self.label(next_block)

    def call(
        self,
        name: str,
        result: str,
        *args: tuple[str, str | int],
        nullable: bool = False,
    ) -> str:
        types = ", ".join(kind for kind, _ in args)
        self.declarations[name] = f"declare {result} @{name}({types})"
        operands = ", ".join(f"{kind} {value}" for kind, value in args)
        instruction = f"call {result} @{name}({operands})"
        if result == "void":
            self.emit(instruction)
            return ""
        value = self.fresh("%v")
        self.emit(f"{value} = {instruction}")
        if result == "ptr" and not nullable:
            test = self.fresh("%valid")
            self.emit(f"{test} = icmp ne ptr {value}, null")
            self.guard(test)
        return value

    def value(self, name: str, *args: str) -> str:
        return self.native(name, "ptr", *(("ptr", arg) for arg in args))

    def native(
        self,
        name: str,
        result: str,
        *args: tuple[str, str | int],
        nullable: bool = False,
    ) -> str:
        return self.call(
            f"ctk_jit_value_{name}_v1",
            result,
            ("ptr", "%values"),
            *args,
            nullable=nullable,
        )

    def literal(self, value: object) -> str:
        if value is None:
            type_id, encoded = 0, ""
        elif isinstance(value, bool):
            type_id, encoded = 1, "true" if value else "false"
        elif isinstance(value, int):
            type_id, encoded = 2, str(value)
        elif isinstance(value, float):
            type_id, encoded = 3, repr(value)
        elif isinstance(value, str):
            type_id, encoded = 4, value
        else:
            raise ValueError(f"unsupported native literal {value!r}")
        return self.native(
            "literal",
            "ptr",
            ("ptr", self.string(encoded)),
            ("i64", len(encoded.encode())),
            ("i32", type_id),
        )

    def stop(self) -> str:
        cleanups, failure = self.cleanups, self.failure
        for index in range(len(cleanups) - 1, -1, -1):
            cleanup, _depth, enclosing = cleanups[index]
            self.cleanups = cleanups[:index]
            self.failure = enclosing
            self.expression(cleanup)
        self.cleanups, self.failure = cleanups, failure
        self.native("exit", "void")
        self.emit("ret i32 0" if self.return_type == "i32" else "ret ptr null")
        self.label(self.fresh("after.exit"))
        return self.literal(None)

    def print_value(self, value: str) -> str:
        return self.call(
            "ctk_jit_value_print_v2", "ptr", ("ptr", "%values"), ("ptr", value)
        )

    def collection(self, kind: int) -> str:
        return self.native("new", "ptr", ("i32", kind))

    def define(self, name: str, value: str, ordinal: str | int = -1) -> None:
        self.native(
            "define",
            "void",
            ("ptr", self.string(name)),
            ("ptr", value),
            ("i64", ordinal),
        )

    def truth(self, value: str) -> str:
        status = self.native("truth", "i32", ("ptr", value))
        valid = self.fresh("%valid")
        self.emit(f"{valid} = icmp sge i32 {status}, 0")
        self.guard(valid)
        truth = self.fresh("%truth")
        self.emit(f"{truth} = icmp eq i32 {status}, 1")
        return truth

    def branch(self, target: str) -> None:
        self.emit(f"br label %{target}")

    def push(self) -> None:
        self.native("push", "void")
        self.scope_depth += 1

    def pop(self) -> None:
        self.native("pop", "void")
        self.scope_depth -= 1

    def statements(
        self, items: Sequence[Node], *, collect: bool, display: bool = False
    ) -> str:
        handlers = {
            item.value: item.children[0] for item in items if item.kind == "handler"
        }
        body = [item for item in items if item.kind != "handler"]
        if "exit" not in handlers:
            return self.recover_body(
                body, handlers.get("error"), collect=collect, display=display
            )

        cleanup = handlers["exit"]
        enclosing = self.failure
        failed, done = self.fresh("exit.failure"), self.fresh("exit.done")
        self.failure = failed
        self.cleanups.append((cleanup, self.scope_depth, enclosing))
        result = self.recover_body(
            body, handlers.get("error"), collect=collect, display=display
        )
        self.cleanups.pop()
        self.failure = enclosing
        self.expression(cleanup)
        self.branch(done)

        self.label(failed)
        self.native("unwind", "void", ("i64", self.scope_depth))
        error = self.value("save_error")
        self.expression(cleanup)
        self.native("restore_error", "void", ("ptr", error))
        self.branch(enclosing)
        self.label(done)
        return result

    def recover_body(
        self,
        items: Sequence[Node],
        handler: Node | None,
        *,
        collect: bool,
        display: bool,
    ) -> str:
        enclosing = self.failure
        if handler is not None:
            recover, done = self.fresh("catch"), self.fresh("handled")
            self.failure = recover
        result = self.literal(None)
        for index, item in enumerate(items):
            if self.match_origin:
                line, column = self.source_location(item.line, item.column)
                self.native("match_location", "void", ("i64", line), ("i64", column))
            visible = display and item.kind not in {
                "let",
                "destructure",
                "runnable",
                "assign",
                "print",
            }
            if item.kind == "host" and item.value[1] == "statement":
                visible = False
            offset = self.native("output_size", "i64") if visible else None
            result = self.expression(item, collect=collect and index == len(items) - 1)
            if offset is not None:
                self.call(
                    "ctk_jit_value_display_v2",
                    "ptr",
                    ("ptr", "%values"),
                    ("ptr", result),
                    ("i64", offset),
                    ("i32", int(item.kind == "foreach")),
                )
        if handler is None:
            return result
        first = self.block
        self.branch(done)
        self.label(recover)
        self.failure = enclosing
        self.native("unwind", "void", ("i64", self.scope_depth))
        self.check(self.native("recover", "i32"))
        other = self.expression(handler)
        second = self.block
        self.branch(done)
        self.label(done)
        value = self.fresh("%handled")
        self.emit(f"{value} = phi ptr [{result}, %{first}], [{other}, %{second}]")
        return value

    def conditional(self, node: Node) -> str:
        condition, yes, no = node.children
        yes_label, no_label, done = (
            self.fresh("then"),
            self.fresh("else"),
            self.fresh("merge"),
        )
        test = self.truth(self.expression(condition))
        self.emit(f"br i1 {test}, label %{yes_label}, label %{no_label}")
        self.label(yes_label)
        yes_value = self.expression(yes)
        yes_end = self.block
        self.branch(done)
        self.label(no_label)
        no_value = self.expression(no)
        no_end = self.block
        self.branch(done)
        self.label(done)
        result = self.fresh("%choice")
        self.emit(
            f"{result} = phi ptr [{yes_value}, %{yes_end}], [{no_value}, %{no_end}]"
        )
        return result

    def logical(self, op: str, left: Node, right: Node) -> str:
        left_value = self.expression(left)
        test = self.truth(left_value)
        left_end = self.block
        rhs, done = self.fresh("rhs"), self.fresh("logic")
        yes, no = (rhs, done) if op == "and" else (done, rhs)
        self.emit(f"br i1 {test}, label %{yes}, label %{no}")
        self.label(rhs)
        right_value = self.expression(right)
        self.truth(right_value)
        right_end = self.block
        self.branch(done)
        self.label(done)
        result = self.fresh("%boolean")
        self.emit(
            f"{result} = phi ptr [{left_value}, %{left_end}], [{right_value}, %{right_end}]"
        )
        return result

    def consumed(self, node: Node) -> str:
        enclosing = self.failure
        failed, done = self.fresh("consume.failed"), self.fresh("consume.done")
        self.failure = failed
        self.native("consume_begin", "void")
        self.consume_depth += 1
        value = self.expression(node)
        self.consume_depth -= 1
        self.failure = enclosing
        self.native("consume_end", "void")
        self.branch(done)
        self.label(failed)
        self.native("consume_end", "void")
        self.branch(enclosing)
        self.label(done)
        return value

    def assign(self, node: Node) -> str:
        target, expression = node.children
        op = node.value
        if target.kind == "ref":
            name = self.string(target.value)
            old = self.value("lookup", name) if op != "=" else None
            value = self.consumed(expression)
            if old is not None:
                value = self.value("binary", self.string(op[:-1]), old, value)
            return self.value("assign", name, value)
        if target.kind not in {"get", "index"}:
            raise unsupported(target, "invalid native assignment target")
        base = self.expression(target.children[0])
        key = (
            self.literal(target.value)
            if target.kind == "get"
            else self.expression(target.children[1])
        )
        old = self.value("index", base, key) if op != "=" else None
        value = self.consumed(expression)
        if old is not None:
            value = self.value("binary", self.string(op[:-1]), old, value)
        return self.value("store", base, key, value)

    def pattern(self, pattern: object, value: str) -> None:
        # Validate all parts before updating any session binding.
        bindings: list[tuple[str, str]] = []

        def match(part: object, operand: str) -> None:
            if isinstance(part, str):
                if part != "_":
                    bindings.append((part, operand))
                return
            if isinstance(part, ConsPattern):
                checked = self.native(
                    "pattern",
                    "ptr",
                    ("ptr", operand),
                    ("i32", 2),
                    ("i64", 1),
                )
                item = self.native("at", "ptr", ("ptr", checked), ("i64", 0))
                tail = self.value("tail", checked)
                match(part.head, item)
                match(part.tail, tail)
                return
            if isinstance(part, ListPattern):
                items, kind = part.elements, 0
            elif isinstance(part, tuple):
                items, kind = part, 1
            else:
                raise ValueError(f"invalid native pattern {part!r}")
            checked = self.native(
                "pattern",
                "ptr",
                ("ptr", operand),
                ("i32", kind),
                ("i64", len(items)),
            )
            for index, item in enumerate(items):
                element = self.native("at", "ptr", ("ptr", checked), ("i64", index))
                match(item, element)

        match(pattern, value)
        for name, operand in bindings:
            self.define(name, operand)

    def check(self, status: str) -> None:
        valid = self.fresh("%valid")
        self.emit(f"{valid} = icmp eq i32 {status}, 0")
        self.guard(valid)

    def foreach(self, node: Node) -> str:
        source, body = node.children
        items = self.value("iterate", self.expression(source))
        result = self.collection(0)
        start = self.block
        header, iteration, step, done = (
            self.fresh("foreach"),
            self.fresh("item"),
            self.fresh("advance"),
            self.fresh("end"),
        )
        index, next_index = self.fresh("%index"), self.fresh("%index")
        self.branch(header)
        self.label(header)
        self.emit(f"{index} = phi i64 [0, %{start}], [{next_index}, %{step}]")
        size = self.native("size", "i64", ("ptr", items))
        more = self.fresh("%more")
        self.emit(f"{more} = icmp ult i64 {index}, {size}")
        self.emit(f"br i1 {more}, label %{iteration}, label %{done}")
        self.label(iteration)
        self.check(self.native("tick", "i32"))
        item = self.native("at", "ptr", ("ptr", items), ("i64", index))
        self.loops.append(
            (done, step, self.scope_depth, len(self.cleanups), self.consume_depth)
        )
        self.push()
        if isinstance(node.value, str) and node.value != "_":
            self.define(node.value, item, index)
        else:
            self.pattern(node.value, item)
        value = self.expression(body)
        self.pop()
        self.loops.pop()
        self.value("add", result, "null", value)
        self.branch(step)
        self.label(step)
        self.emit(f"{next_index} = add i64 {index}, 1")
        self.branch(header)
        self.label(done)
        return result

    def condition_loop(self, node: Node, collect: bool) -> str:
        condition, body = node.children
        check, iteration, done = (
            self.fresh("check"),
            self.fresh("iteration"),
            self.fresh("end"),
        )
        result = self.collection(0) if collect else self.literal(None)
        repeat = node.kind == "repeat"
        self.branch(iteration if repeat else check)
        self.label(check)
        test = self.truth(self.expression(condition))
        yes, no = (done, iteration) if repeat else (iteration, done)
        self.emit(f"br i1 {test}, label %{yes}, label %{no}")
        self.label(iteration)
        self.check(self.native("tick", "i32"))
        self.loops.append(
            (done, check, self.scope_depth, len(self.cleanups), self.consume_depth)
        )
        self.push()
        value = self.expression(body, collect=collect)
        self.pop()
        self.loops.pop()
        if collect:
            self.value("add", result, "null", value)
        self.branch(check)
        self.label(done)
        return result

    def invoke(self, node: Node, injected: str | None = None) -> str:
        arguments = self.collection(0)
        keywords = self.collection(2)
        if injected is not None:
            self.value("add", arguments, "null", injected)
        if node.kind == "invoke":
            callee = self.expression(node.children[0])
            parameters = node.children[1:]
        else:
            callee = None
            parameters = node.children
        names: set[str] = set()
        for parameter in parameters:
            if parameter.kind == "keyword_arg":
                if parameter.value in names:
                    raise unsupported(parameter, "duplicate keyword argument")
                names.add(parameter.value)
                key = self.literal(parameter.value)
                value = self.expression(parameter.children[0])
                self.value("add", keywords, key, value)
            else:
                if names:
                    raise unsupported(
                        parameter, "positional arguments must precede keywords"
                    )
                self.value("add", arguments, "null", self.expression(parameter))
        if callee is not None:
            return self.value("invoke", callee, arguments, keywords)
        if node.value == "ctk":
            return self.call(
                "ctk_jit_eval_v1",
                "ptr",
                ("ptr", "%context"),
                ("ptr", arguments),
                ("ptr", keywords),
            )
        return self.value("call", self.string(node.value), arguments, keywords)

    def parameters(self, node: Node, *, positional_only: bool) -> None:
        _, parameters = node.value
        defaults = node.children[1:]
        required = len(parameters) - len(defaults)
        labels = []
        for index, pattern in enumerate(parameters):
            label = (
                node.parameter_labels[index]
                if index < len(node.parameter_labels)
                else None
            )
            if label is None and isinstance(pattern, str) and pattern != "_":
                label = pattern
            labels.append(
                self.string(label)
                if label is not None and not positional_only
                else "null"
            )
        data = ", ".join(f"ptr {label}" for label in labels)
        table = self.constant(f"[{len(labels)} x ptr] [{data}]") if labels else "null"
        status = self.native(
            "check_arguments",
            "i32",
            ("ptr", "%arguments"),
            ("ptr", "%keywords"),
            ("ptr", table),
            ("i64", len(parameters)),
            ("i64", required),
        )
        self.check(status)
        for index, (pattern, label) in enumerate(zip(parameters, labels, strict=True)):
            argument = self.native(
                "argument",
                "ptr",
                ("ptr", "%arguments"),
                ("ptr", "%keywords"),
                ("i64", index),
                ("ptr", label),
                nullable=True,
            )
            if index >= required:
                present = self.fresh("%present")
                self.emit(f"{present} = icmp ne ptr {argument}, null")
                supplied = self.block
                default, done = self.fresh("default"), self.fresh("arg")
                self.emit(f"br i1 {present}, label %{done}, label %{default}")
                self.label(default)
                fallback = self.expression(defaults[index - required].children[0])
                default_end = self.block
                self.branch(done)
                self.label(done)
                value = self.fresh("%parameter")
                self.emit(
                    f"{value} = phi ptr [{argument}, %{supplied}], [{fallback}, %{default_end}]"
                )
            else:
                value = argument
            self.pattern(pattern, value)

    def source_location(self, line: int, column: int) -> tuple[int, int]:
        if self.match_origin:
            start_line, start_column = self.match_origin
            return start_line + line - 1, column + (start_column if line == 1 else 0)
        return line, column

    def match_body(
        self,
        program: Node,
        host: Callable[[LanguageIR, Node], str],
        origin: tuple[int, int],
    ) -> str:
        child, slot, symbol = self._callable_body(host)
        child.match_origin = origin
        child.value("match_bindings", "%arguments")
        child.statements(program.children, collect=False, display=True)
        result = child.literal(None)
        child.emit(f"ret ptr {result}")
        return self._finish_callable(child, slot, symbol, "", 0, 0)

    def check_exit(self) -> None:
        requested = self.native("exit_requested", "i32")
        exiting = self.fresh("%exiting")
        self.emit(f"{exiting} = icmp ne i32 {requested}, 0")
        stop, proceed = self.fresh("stop"), self.fresh("proceed")
        self.emit(f"br i1 {exiting}, label %{stop}, label %{proceed}")
        self.label(stop)
        self.stop()
        self.branch(proceed)
        self.label(proceed)

    def _callable_body(
        self, host: Callable[[LanguageIR, Node], str]
    ) -> tuple[LanguageIR, int, str]:
        slot = len(self.functions)
        self.functions.append("")
        symbol = f"ctk.runnable.{slot}"
        child = LanguageIR(self.string, self.constant, host)
        child.return_type = "ptr"
        child.declarations = self.declarations
        child.functions = self.functions
        return child, slot, symbol

    def _finish_callable(
        self,
        child: LanguageIR,
        slot: int,
        symbol: str,
        name: str,
        minimum: int,
        maximum: int,
    ) -> str:
        child.label("error")
        child.emit("ret ptr null")
        body = "\n".join(child.lines)
        self.functions[slot] = (
            f"define internal ptr @{symbol}(ptr %context, ptr %values, ptr %arguments, ptr %keywords) {{\n"
            f"entry:\n{body}\n}}"
        )
        return self.call(
            "ctk_jit_value_runnable_v2",
            "ptr",
            ("ptr", "%values"),
            ("ptr", self.string(name)),
            ("ptr", f"@{symbol}"),
            ("i64", minimum),
            ("i64", maximum),
        )

    def runnable(self, node: Node) -> str:
        child, slot, symbol = self._callable_body(self.host)
        if node.kind == "clause_runnable":
            name = node.value
            for clause in node.children:
                child.push()
                next_clause = child.fresh("next.clause")
                child.failure = next_clause
                child.parameters(clause, positional_only=True)
                child.failure = "error"
                result = child.expression(clause.children[0])
                child.pop()
                child.emit(f"ret ptr {result}")
                child.label(next_clause)
                child.native("pop", "void")
                child.native("clear_error", "void")
            message = child.string(f"no matching clause for {name}")
            child.native("fail", "void", ("ptr", message))
            child.branch("error")
        else:
            name, _ = node.value
            child.parameters(node, positional_only=False)
            result = child.expression(node.children[0])
            child.emit(f"ret ptr {result}")
        signature = node.children[0] if node.kind == "clause_runnable" else node
        arity = len(signature.value[1])
        value = self._finish_callable(
            child, slot, symbol, name, arity - len(signature.children[1:]), arity
        )
        if node.kind == "runnable":
            self.define(name, value)
        return value

    def recovery(self, node: Node) -> str:
        expression, fallback = node.children
        recover, done = self.fresh("recover"), self.fresh("recovered")
        enclosing = self.failure
        self.failure = recover
        self.push()
        result = self.expression(expression)
        self.pop()
        first = self.block
        self.branch(done)
        self.label(recover)
        # The native runtime unwinds scopes left open by a failing expression.
        self.native("unwind", "void", ("i64", self.scope_depth))
        self.failure = enclosing
        self.check(self.native("recover", "i32"))
        other = self.expression(fallback)
        second = self.block
        self.branch(done)
        self.label(done)
        value = self.fresh("%recovered")
        self.emit(f"{value} = phi ptr [{result}, %{first}], [{other}, %{second}]")
        return value

    def expression(self, node: Node, *, collect: bool = True) -> str:
        kind, op, children = node.kind, node.value, node.children
        if kind == "literal":
            return self.literal(op)
        if kind == "ref":
            return self.value("lookup", self.string(op))
        if kind in {"list", "tuple", "dict"}:
            result = self.collection({"list": 0, "tuple": 1, "dict": 2}[kind])
            for item in children:
                key = self.literal(item.value) if kind == "dict" else "null"
                value = self.expression(item.children[0] if kind == "dict" else item)
                self.value("add", result, key, value)
            return result
        if kind == "get":
            (base,) = children
            return self.value(
                "get",
                self.expression(base),
                self.string(op),
                self.string(base.value) if base.kind == "ref" else "null",
            )
        if kind == "index":
            base, key = children
            value = self.expression(base)
            if key.kind == "slice":
                bounds = [
                    "null" if bound.kind == "omitted" else self.expression(bound)
                    for bound in key.children
                ]
                return self.value("slice", value, *bounds)
            return self.value("index", value, self.expression(key))
        if kind == "binary":
            left, right = children
            if op in {"and", "or"}:
                return self.logical(op, left, right)
            return self.value(
                "binary", self.string(op), self.expression(left), self.expression(right)
            )
        if kind == "unary":
            return self.value("unary", self.string(op), self.expression(children[0]))
        if kind == "predicate":
            if op in {"is_defined", "is_not_defined", "is_set", "is_not_set"}:
                (target,) = children
                if target.kind != "ref":
                    raise unsupported(target, "binding predicate requires a reference")
                return self.native(
                    "binding_test",
                    "ptr",
                    ("ptr", self.string(target.value)),
                    ("i32", int(op.endswith("set"))),
                    ("i32", int("_not_" in op)),
                )
            if op in {"has", "does_not_have", "in", "not_in", "is_kind", "is_not_kind"}:
                return self.value(
                    "predicate",
                    self.string(op),
                    *(self.expression(x) for x in children),
                )
            raise unsupported(node, f"unsupported native predicate {op!r}")
        if kind == "let":
            value = self.consumed(children[0])
            self.define(op, value)
            return value
        if kind == "destructure":
            value = self.consumed(children[0])
            self.pattern(op, value)
            return value
        if kind == "assign":
            return self.assign(node)
        if kind == "print":
            value = self.expression(children[0])
            return self.print_value(value)
        if kind == "conditional":
            return self.conditional(node)
        if kind == "block":
            self.push()
            result = self.statements(children, collect=collect)
            self.pop()
            return result
        if kind == "foreach":
            return self.foreach(node)
        if kind in {"while", "repeat"}:
            return self.condition_loop(node, collect)
        if kind == "flow":
            done, advance, depth, cleanup_count, consume_depth = self.loops[-1]
            cleanups, original_depth, original_failure = (
                self.cleanups,
                self.scope_depth,
                self.failure,
            )
            for index in range(len(cleanups) - 1, cleanup_count - 1, -1):
                cleanup, cleanup_depth, failure = cleanups[index]
                self.cleanups = cleanups[:index]
                self.scope_depth, self.failure = cleanup_depth, failure
                self.native("unwind", "void", ("i64", cleanup_depth))
                self.expression(cleanup)
            self.native("unwind", "void", ("i64", depth))
            for _ in range(consume_depth, self.consume_depth):
                self.native("consume_end", "void")
            self.cleanups, self.scope_depth, self.failure = (
                cleanups,
                original_depth,
                original_failure,
            )
            self.branch(done if op == "break" else advance)
            self.label(self.fresh("unreachable"))
            return self.literal(None)
        if kind in {"call", "invoke"}:
            return self.invoke(node)
        if kind == "pipe":
            result = self.expression(children[0])
            for stage in children[1:]:
                result = self.invoke(stage, result)
            return result
        if kind in {"runnable", "inline_runnable", "clause_runnable"}:
            return self.runnable(node)
        if kind == "recovery":
            return self.recovery(node)
        if kind == "consume":
            return self.consumed(children[0])
        if kind == "host":
            return self.host(self, node)
        raise unsupported(node, f"unsupported native CTK construct {kind!r}")

    def program(
        self, program: Node, *, display: bool, path: str | None
    ) -> tuple[str, str]:
        name = "ctk_jit_value_context_v1"
        self.declarations[name] = f"declare ptr @{name}(ptr)"
        self.emit(f"%values = call ptr @{name}(ptr %context)")
        if path is not None:
            self.native("set_source", "void", ("ptr", self.string(path)))
        result = self.statements(program.children, collect=False, display=display)
        self.native("set_result", "void", ("ptr", result))
        self.emit("ret i32 0")
        self.label("error")
        self.emit("ret i32 1")
        return "\n".join((*self.declarations.values(), *self.functions)), "\n".join(
            self.lines
        )
