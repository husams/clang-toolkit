"""Lexical runnable values shared by the tree and Python AST engines."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, replace
from typing import Any, Callable, Mapping

from .semantics import Context, ExecutionLimitError, PrototypeError, _error, child_values
from .patterns import compile_matcher, pattern_names, format_pattern

_MISSING = object()


@dataclass(frozen=True, repr=False)
class RunnableBlock:
    name: str
    parameters: tuple[Any, ...]
    body: Any
    executable: Callable[[Context], Any]
    scopes: tuple[dict[str, Any], ...]
    source: str
    string_templates: dict[str, Any]
    definition_location: tuple[int | None, int | None]
    source_name: str
    defaults: tuple[Callable[[Context], Any], ...] = ()
    default_nodes: tuple[Any, ...] = ()
    definition: str = ""
    recursion: Any = None
    direct_loop: Any = None

    def __str__(self) -> str:
        return f"{self.name}({', '.join(_format_pattern(item) for item in self.parameters)})"

    def invoke(self, context: Context, node: Any, arguments: list[Any], keywords: Mapping[str, Any] | None = None,
               *, _bound: dict[str, Any] | None = None, _executable: Callable[[Context], Any] | None = None) -> Any:
        runtime = getattr(getattr(context, "session", None), "runtime", None)
        depth = getattr(runtime, "_matcher_call_depth", context.call_depth)
        if depth >= 64:
            raise _error(context, node, "runnable call depth exceeds 64", ExecutionLimitError)
        previous_scopes = list(context._scopes)
        previous_source = context.source
        previous_source_name = context.source_name
        previous_templates = context.string_templates
        supplied: dict[int, Any] = {index: value for index, value in enumerate(arguments)}
        names = {pattern: index for index, pattern in enumerate(self.parameters)
                 if isinstance(pattern, str) and pattern != "_"}
        for key, value in (keywords or {}).items():
            if key not in names:
                raise _error(context, node, f"{self.name} has no parameter {key!r}")
            if names[key] in supplied:
                raise _error(context, node, f"{self.name} got multiple values for {key!r}")
            supplied[names[key]] = value
        from .list_recursion import observer_allows_optimization

        if self.recursion is not None and _executable is None and observer_allows_optimization(context):
            _bound = {}
            _executable = lambda ctx: self.recursion.run(ctx, arguments, self, node)
        local: dict[str, Any] = {self.name: self}
        if _bound is not None:
            local.update(_bound)
        else:
            for index, pattern in enumerate(self.parameters):
                if index in supplied:
                    bind_pattern(local, pattern, supplied[index], context, node)
        context.call_depth += 1
        if runtime is not None:
            runtime._matcher_call_depth += 1
        context._scopes[:] = [*self.scopes, local]
        context.source = self.source
        context.source_name = self.source_name
        context.string_templates = self.string_templates
        try:
            for index, default in enumerate(self.defaults, start=len(self.parameters) - len(self.defaults)):
                if index not in supplied:
                    bind_pattern(context._scopes[-1], self.parameters[index], default(context), context, node)
            return (_executable or self.executable)(context)
        except Exception as error:
            if not getattr(error, "runnable_frame", False):
                line, column = self.definition_location
                detail = (f"{error}; runnable {self.name} defined at line {line}, column {column} in {self.source_name}, "
                          f"called at line {getattr(node, 'line', None)}, column {getattr(node, 'column', None)} in {previous_source_name}")
                kind = type(error) if isinstance(error, PrototypeError) else PrototypeError
                framed = kind(detail)
                framed.runnable_frame = True
                raise framed from error
            raise
        finally:
            context._scopes[:] = previous_scopes
            context.source = previous_source
            context.source_name = previous_source_name
            context.string_templates = previous_templates
            context.call_depth -= 1
            if runtime is not None:
                runtime._matcher_call_depth -= 1


@dataclass(frozen=True, repr=False)
class MultiClauseBlock(RunnableBlock):
    matchers: tuple[Callable[[list[Any]], dict[str, Any] | None], ...] = ()
    executables: tuple[Callable[[Context], Any], ...] = ()
    optimized: Callable[[Context, list[Any], Any], Any] | None = None

    def invoke(self, context: Context, node: Any, arguments: list[Any], keywords: Mapping[str, Any] | None = None) -> Any:
        if keywords:
            raise _error(context, node, "multi-clause functions accept positional arguments only")
        from .list_recursion import observer_allows_optimization

        allowed = observer_allows_optimization(context)
        if self.optimized is not None and allowed:
            return super().invoke(context, node, arguments, _bound={},
                                  _executable=lambda ctx: self.optimized(ctx, arguments, node))
        if self.direct_loop is not None and allowed:
            return super().invoke(context, node, arguments, _bound={},
                                  _executable=lambda ctx: self.direct_loop(ctx, arguments, self, node))
        if self.recursion is not None and allowed:
            return super().invoke(context, node, arguments, _bound={},
                                  _executable=lambda ctx: self.recursion.run(ctx, arguments, self, node))
        for matcher, executable in zip(self.matchers, self.executables):
            context.tick(self.body)
            bindings = matcher(arguments)
            if bindings is not None:
                return super().invoke(context, node, arguments, _bound=bindings, _executable=executable)
        raise _error(context, node, f"no matching clause for {self.name}")


def create_clause_runnable(context: Context, node: Any,
                           executables: tuple[Callable[[Context], Any], ...]) -> MultiClauseBlock:
    from .folds import compile_right_fold
    from .list_loops import compile_direct_loop
    from .list_recursion import compile_list_recursion

    parameters = node.children[0].value[1]
    return MultiClauseBlock(
        name=node.value, parameters=parameters, body=node, executable=executables[0],
        scopes=context.scopes, source=context.source, string_templates=context.string_templates,
        definition_location=(node.line, node.column), source_name=context.source_name,
        definition=context.source[slice(*node.source_span)] if node.source_span else "",
        matchers=tuple(compile_matcher(clause.value[1]) for clause in node.children),
        executables=executables, optimized=compile_right_fold(node), recursion=compile_list_recursion(node, context),
        direct_loop=compile_direct_loop(node, context),
    )


def define_runnable(context: Context, node: Any, executable: Callable[[Context], Any],
                    defaults: tuple[Callable[[Context], Any], ...] = ()) -> RunnableBlock:
    from clang_toolkit.cli.matcher_catalog import SCRIPT_BUILTIN_MATCHERS

    name, parameters = node.value
    if ((name in context.functions and name not in getattr(context, "filter_names", set()))
            or name in SCRIPT_BUILTIN_MATCHERS | {"glob"}):
        raise _error(context, node, f"{name} is a built-in callable name")
    value = create_runnable(context, node, executable, defaults)
    context.define(name, value)
    return value


def create_runnable(context: Context, node: Any, executable: Callable[[Context], Any],
                    defaults: tuple[Callable[[Context], Any], ...] = ()) -> RunnableBlock:
    """Create a dormant lexical callable without adding a binding."""
    name, parameters = node.value
    names = [item for pattern in parameters for item in _pattern_names(pattern)]
    if len(set(names)) != len(names):
        raise _error(context, node, f"{name} has duplicate parameter names")
    from .list_recursion import compile_list_recursion

    value = RunnableBlock(name, parameters, node.children[0], executable,
                          context.scopes, context.source, context.string_templates,
                          (node.line, node.column), context.source_name, defaults, node.children[1:],
                          context.source[slice(*node.source_span)] if node.source_span else "",
                          compile_list_recursion(node, context))
    return value


def invoke_named(context: Context, node: Any, name: str,
                 arguments: Callable[[], list[Any]], *, injected: Any = _MISSING) -> Any:
    present, value = context.binding_state(name, node)
    if not present:
        value = context.functions.get(name)
        present = value is not None
    if not present:
        raise _error(context, node, f"unregistered host function {name!r}")
    return invoke_value(context, node, value, arguments, name=name, injected=injected)


def invoke_value(context: Context, node: Any, value: Any,
                 arguments: Callable[[], list[Any]], *, name: str = "<expression>",
                 injected: Any = _MISSING) -> Any:
    """Invoke an already evaluated callee, checking arguments before effects."""
    value = _current_filter_callable(context, value)
    positional_nodes = [item for item in child_values(node) if getattr(item, "kind", None) != "keyword_arg"]
    keyword_nodes = [item for item in child_values(node) if getattr(item, "kind", None) == "keyword_arg"]
    keyword_names = [str(item.value) for item in keyword_nodes]
    if len(set(keyword_names)) != len(keyword_names):
        raise _error(context, node, f"{name} got a duplicate keyword argument")
    seen_keyword = False
    for item in child_values(node):
        is_keyword = getattr(item, "kind", None) == "keyword_arg"
        if is_keyword:
            seen_keyword = True
        elif seen_keyword:
            raise _error(context, item, f"{name} positional arguments must precede named arguments")
    count = len(positional_nodes) + (1 if injected is not _MISSING else 0)
    keywords = tuple(keyword_names)
    _preflight(context, node, name, value, count, keywords)
    supplied = arguments()
    positional = [injected] if injected is not _MISSING else []
    named: dict[str, Any] = {}
    supplied_iter = iter(supplied)
    for item in child_values(node):
        value_arg = next(supplied_iter)
        if getattr(item, "kind", None) == "keyword_arg":
            named[str(item.value)] = value_arg
        else:
            positional.append(value_arg)
    return invoke_prepared(context, node, value, positional, named)


def invoke_prepared(context: Context, node: Any, value: Any, positional: list[Any], named: Mapping[str, Any]) -> Any:
    """Dispatch an already validated callee without repeating observable checks."""
    if isinstance(value, RunnableBlock):
        return value.invoke(context, node, positional, named)
    try:
        from clang_toolkit.cli.runtime.matcher_functions import MatcherFunction
    except ImportError:
        MatcherFunction = ()  # type: ignore[assignment,misc]
    if isinstance(value, MatcherFunction):
        runtime = getattr(getattr(context, "session", None), "runtime", None)
        if runtime is None:
            raise _error(context, node, f"{getattr(node, 'value', '<expression>')!r} is not callable")
        if named:
            raise _error(context, node, f"{getattr(node, 'value', '<expression>')} does not accept named arguments")
        return value.call(runtime, positional)
    if callable(value):
        return value(*positional, **named)
    raise _error(context, node, f"{getattr(node, 'value', '<expression>')!r} is not callable")


def _preflight(context: Context, node: Any, name: str, value: Any, positional_count: int,
               keywords: tuple[str, ...]) -> None:
    value = _current_filter_callable(context, value)
    if isinstance(value, RunnableBlock):
        if isinstance(value, MultiClauseBlock) and keywords:
            raise _error(context, node, "multi-clause functions accept positional arguments only")
        required = len(value.parameters) - len(value.defaults)
        names = {item for item in value.parameters if isinstance(item, str) and item != "_"}
        if any(key not in names for key in keywords):
            unknown = next(key for key in keywords if key not in names)
            raise _error(context, node, f"{name} has no parameter {unknown!r}")
        assigned = set(range(positional_count))
        keyword_slots = {value.parameters.index(key) for key in keywords if key in names}
        duplicates = assigned & keyword_slots
        if duplicates:
            raise _error(context, node, f"{name} got multiple values for {value.parameters[min(duplicates)]!r}")
        total = positional_count + len(keywords)
        supplied_slots = assigned | keyword_slots
        if positional_count > len(value.parameters) or not set(range(required)).issubset(supplied_slots):
            if not value.defaults:
                raise _error(context, node, f"{name} expects {len(value.parameters)} argument(s), got {total}")
            raise _error(context, node, f"{name} expects {required}..{len(value.parameters)} argument(s), got {total}")
        return
    try:
        from clang_toolkit.cli.runtime.matcher_functions import MatcherFunction
    except ImportError:
        MatcherFunction = ()  # type: ignore[assignment,misc]
    if isinstance(value, MatcherFunction):
        if keywords or positional_count != len(value.parameters):
            raise _error(context, node, f"{name} expects {len(value.parameters)} positional argument(s)")
        return
    if not callable(value):
        raise _error(context, node, f"{name!r} is not callable")
    try:
        signature = inspect.signature(value)
    except (TypeError, ValueError):
        # Some extension and built-in callables do not publish a signature;
        # preserve their native argument validation when they are invoked.
        return
    try:
        signature.bind(*([None] * positional_count), **{key: None for key in keywords})
    except TypeError as error:
        raise _error(context, node, f"invalid arguments for {name}: {error}") from error


def bind_pattern(target: dict[str, Any], pattern: Any, value: Any, context: Context, node: Any) -> None:
    bindings = compile_matcher((pattern,))([value])
    if bindings is None:
        if isinstance(pattern, tuple):
            raise _error(context, node, f"tuple pattern expects {len(pattern)} element(s), got {len(value) if isinstance(value, tuple) else type(value).__name__}")
        raise _error(context, node, f"pattern {format_pattern(pattern)} does not match {type(value).__name__}")
    target.update(bindings)


def _pattern_names(pattern: Any) -> tuple[str, ...]:
    return pattern_names(pattern)


def _format_pattern(pattern: Any) -> str:
    return format_pattern(pattern)


def prepare_callback(context: Context, node: Any, callback: Any) -> Callable[[Any], Any]:
    """Adapt one runnable callback according to its declared required arity."""
    callback = _current_filter_callable(context, callback)
    if not isinstance(callback, RunnableBlock) and not callable(callback):
        raise _error(context, node, "callback must be callable")
    if isinstance(callback, RunnableBlock):
        required_count = len(callback.parameters) - len(callback.defaults)
        expand = required_count > 1
    else:
        try:
            signature = inspect.signature(callback)
            required = [parameter for parameter in signature.parameters.values()
                        if parameter.kind in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)
                        and parameter.default is parameter.empty]
        except (TypeError, ValueError):
            signature = None
            required = []
        required_count = len(required)
        expand = len(required) > 1
    # Validate the chosen calling mode before touching the input iterable. This
    # makes invalid callbacks fail even when the sequence is empty.
    callback_name = getattr(callback, "name", getattr(callback, "__name__", "callback"))
    _preflight(context, node, str(callback_name), callback, required_count if expand else 1, ())

    def invoke(item: Any) -> Any:
        args = list(item) if expand and isinstance(item, tuple) else [item]
        if expand and not isinstance(item, tuple):
            raise _error(context, node, f"callback expects a tuple item with {required_count} value(s)")
        if isinstance(callback, RunnableBlock):
            _preflight(context, node, callback.name, callback, len(args), ())
            return callback.invoke(context, node, args)
        if signature is not None:
            try:
                signature.bind(*([None] * len(args)))
            except TypeError as error:
                raise _error(context, node, f"invalid callback arguments: {error}") from error
        return callback(*args)
    return invoke


def _current_filter_callable(context: Context, value: Any) -> Any:
    name = getattr(value, "__ctk_filter_name__", None)
    if isinstance(name, str):
        return context.functions.get(name, value)
    return value


def run_pipe(context: Context, node: Any, initial: Callable[[], Any], stages: list[tuple[Any, str, Callable[[], list[Any]]]]) -> Any:
    """Evaluate a left-to-right chain, injecting each value as arg zero."""
    value = initial()
    for index, (stage, name, arguments) in enumerate(stages, start=1):
        context.tick(stage)
        try:
            if getattr(stage, "kind", None) == "ref":
                arguments = lambda: []
            value = invoke_named(context, stage, name, arguments, injected=value)
        except PrototypeError as error:
            raise _error(context, stage, f"pipe stage {index} {name!r} failed: {error}", type(error)) from error
        except Exception as error:
            raise _error(context, stage, f"pipe stage {index} {name!r} failed: {error}") from error
    return value


def snapshot_scopes(scopes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Freeze plain captures for one group, preserving aliases and recursion."""
    copies: dict[int, Any] = {}

    def copy(value: Any) -> Any:
        if id(value) in copies:
            return copies[id(value)]
        if isinstance(value, RunnableBlock):
            result = replace(value, scopes=())
            copies[id(value)] = result
            object.__setattr__(result, "scopes", tuple(copy(scope) for scope in value.scopes))
            return result
        if type(value) is dict:
            result = {}
            copies[id(value)] = result
            result.update((key, copy(item)) for key, item in value.items())
            return result
        if type(value) is list:
            result = []
            copies[id(value)] = result
            result.extend(copy(item) for item in value)
            return result
        if type(value) is tuple:
            return tuple(copy(item) for item in value)
        # Native objects retain their ownership and stale-handle checks.
        return value

    return [copy(scope) for scope in scopes]
