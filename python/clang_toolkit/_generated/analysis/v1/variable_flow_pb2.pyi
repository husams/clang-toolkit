from ...match.v1 import match_service_pb2 as _match_service_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class VariableFlowRequest(_message.Message):
    __slots__ = ("variable", "function", "resource_scope_id", "max_blocks", "max_events", "max_iterations")
    VARIABLE_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_SCOPE_ID_FIELD_NUMBER: _ClassVar[int]
    MAX_BLOCKS_FIELD_NUMBER: _ClassVar[int]
    MAX_EVENTS_FIELD_NUMBER: _ClassVar[int]
    MAX_ITERATIONS_FIELD_NUMBER: _ClassVar[int]
    variable: _match_service_pb2.BindingMatchTarget
    function: _match_service_pb2.BindingMatchTarget
    resource_scope_id: str
    max_blocks: int
    max_events: int
    max_iterations: int
    def __init__(self, variable: _Optional[_Union[_match_service_pb2.BindingMatchTarget, _Mapping]] = ..., function: _Optional[_Union[_match_service_pb2.BindingMatchTarget, _Mapping]] = ..., resource_scope_id: _Optional[str] = ..., max_blocks: _Optional[int] = ..., max_events: _Optional[int] = ..., max_iterations: _Optional[int] = ...) -> None: ...

class VariableFlowLocation(_message.Message):
    __slots__ = ("file", "line", "column")
    FILE_FIELD_NUMBER: _ClassVar[int]
    LINE_FIELD_NUMBER: _ClassVar[int]
    COLUMN_FIELD_NUMBER: _ClassVar[int]
    file: str
    line: int
    column: int
    def __init__(self, file: _Optional[str] = ..., line: _Optional[int] = ..., column: _Optional[int] = ...) -> None: ...

class VariableFlowStarted(_message.Message):
    __slots__ = ("variable", "function", "snapshot_generation", "declaration_id", "declaration", "entry_block", "exit_block")
    VARIABLE_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_GENERATION_FIELD_NUMBER: _ClassVar[int]
    DECLARATION_ID_FIELD_NUMBER: _ClassVar[int]
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    ENTRY_BLOCK_FIELD_NUMBER: _ClassVar[int]
    EXIT_BLOCK_FIELD_NUMBER: _ClassVar[int]
    variable: str
    function: str
    snapshot_generation: int
    declaration_id: int
    declaration: VariableFlowLocation
    entry_block: int
    exit_block: int
    def __init__(self, variable: _Optional[str] = ..., function: _Optional[str] = ..., snapshot_generation: _Optional[int] = ..., declaration_id: _Optional[int] = ..., declaration: _Optional[_Union[VariableFlowLocation, _Mapping]] = ..., entry_block: _Optional[int] = ..., exit_block: _Optional[int] = ...) -> None: ...

class VariableUsage(_message.Message):
    __slots__ = ("id", "block", "element", "kind", "location", "provisional")
    class Kind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        KIND_UNSPECIFIED: _ClassVar[VariableUsage.Kind]
        DECLARE: _ClassVar[VariableUsage.Kind]
        INITIALIZE: _ClassVar[VariableUsage.Kind]
        READ: _ClassVar[VariableUsage.Kind]
        WRITE: _ClassVar[VariableUsage.Kind]
        READ_WRITE: _ClassVar[VariableUsage.Kind]
        ADDRESS_TAKEN: _ClassVar[VariableUsage.Kind]
        UNKNOWN_EFFECT: _ClassVar[VariableUsage.Kind]
    KIND_UNSPECIFIED: VariableUsage.Kind
    DECLARE: VariableUsage.Kind
    INITIALIZE: VariableUsage.Kind
    READ: VariableUsage.Kind
    WRITE: VariableUsage.Kind
    READ_WRITE: VariableUsage.Kind
    ADDRESS_TAKEN: VariableUsage.Kind
    UNKNOWN_EFFECT: VariableUsage.Kind
    ID_FIELD_NUMBER: _ClassVar[int]
    BLOCK_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    PROVISIONAL_FIELD_NUMBER: _ClassVar[int]
    id: int
    block: int
    element: int
    kind: VariableUsage.Kind
    location: VariableFlowLocation
    provisional: bool
    def __init__(self, id: _Optional[int] = ..., block: _Optional[int] = ..., element: _Optional[int] = ..., kind: _Optional[_Union[VariableUsage.Kind, str]] = ..., location: _Optional[_Union[VariableFlowLocation, _Mapping]] = ..., provisional: _Optional[bool] = ...) -> None: ...

class VariableFlowFact(_message.Message):
    __slots__ = ("usage_id", "reachable", "initialization", "reaching_assignments", "live_after", "dead_store")
    class Initialization(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        INITIALIZATION_UNSPECIFIED: _ClassVar[VariableFlowFact.Initialization]
        UNINITIALIZED: _ClassVar[VariableFlowFact.Initialization]
        MAYBE_INITIALIZED: _ClassVar[VariableFlowFact.Initialization]
        INITIALIZED: _ClassVar[VariableFlowFact.Initialization]
        UNKNOWN: _ClassVar[VariableFlowFact.Initialization]
    INITIALIZATION_UNSPECIFIED: VariableFlowFact.Initialization
    UNINITIALIZED: VariableFlowFact.Initialization
    MAYBE_INITIALIZED: VariableFlowFact.Initialization
    INITIALIZED: VariableFlowFact.Initialization
    UNKNOWN: VariableFlowFact.Initialization
    USAGE_ID_FIELD_NUMBER: _ClassVar[int]
    REACHABLE_FIELD_NUMBER: _ClassVar[int]
    INITIALIZATION_FIELD_NUMBER: _ClassVar[int]
    REACHING_ASSIGNMENTS_FIELD_NUMBER: _ClassVar[int]
    LIVE_AFTER_FIELD_NUMBER: _ClassVar[int]
    DEAD_STORE_FIELD_NUMBER: _ClassVar[int]
    usage_id: int
    reachable: bool
    initialization: VariableFlowFact.Initialization
    reaching_assignments: _containers.RepeatedScalarFieldContainer[int]
    live_after: bool
    dead_store: bool
    def __init__(self, usage_id: _Optional[int] = ..., reachable: _Optional[bool] = ..., initialization: _Optional[_Union[VariableFlowFact.Initialization, str]] = ..., reaching_assignments: _Optional[_Iterable[int]] = ..., live_after: _Optional[bool] = ..., dead_store: _Optional[bool] = ...) -> None: ...

class VariableFlowFinding(_message.Message):
    __slots__ = ("kind", "usage_id", "message", "witness_blocks")
    class Kind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        KIND_UNSPECIFIED: _ClassVar[VariableFlowFinding.Kind]
        POSSIBLY_UNINITIALIZED: _ClassVar[VariableFlowFinding.Kind]
        UNINITIALIZED_READ: _ClassVar[VariableFlowFinding.Kind]
        DEAD_STORE: _ClassVar[VariableFlowFinding.Kind]
        UNSUPPORTED_EFFECT: _ClassVar[VariableFlowFinding.Kind]
    KIND_UNSPECIFIED: VariableFlowFinding.Kind
    POSSIBLY_UNINITIALIZED: VariableFlowFinding.Kind
    UNINITIALIZED_READ: VariableFlowFinding.Kind
    DEAD_STORE: VariableFlowFinding.Kind
    UNSUPPORTED_EFFECT: VariableFlowFinding.Kind
    KIND_FIELD_NUMBER: _ClassVar[int]
    USAGE_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    WITNESS_BLOCKS_FIELD_NUMBER: _ClassVar[int]
    kind: VariableFlowFinding.Kind
    usage_id: int
    message: str
    witness_blocks: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, kind: _Optional[_Union[VariableFlowFinding.Kind, str]] = ..., usage_id: _Optional[int] = ..., message: _Optional[str] = ..., witness_blocks: _Optional[_Iterable[int]] = ...) -> None: ...

class VariableFlowCompleted(_message.Message):
    __slots__ = ("usage_count", "fact_count", "finding_count", "block_count", "iterations", "is_complete")
    USAGE_COUNT_FIELD_NUMBER: _ClassVar[int]
    FACT_COUNT_FIELD_NUMBER: _ClassVar[int]
    FINDING_COUNT_FIELD_NUMBER: _ClassVar[int]
    BLOCK_COUNT_FIELD_NUMBER: _ClassVar[int]
    ITERATIONS_FIELD_NUMBER: _ClassVar[int]
    IS_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    usage_count: int
    fact_count: int
    finding_count: int
    block_count: int
    iterations: int
    is_complete: bool
    def __init__(self, usage_count: _Optional[int] = ..., fact_count: _Optional[int] = ..., finding_count: _Optional[int] = ..., block_count: _Optional[int] = ..., iterations: _Optional[int] = ..., is_complete: _Optional[bool] = ...) -> None: ...

class VariableFlowEvent(_message.Message):
    __slots__ = ("started", "usage", "fact", "finding", "completed")
    STARTED_FIELD_NUMBER: _ClassVar[int]
    USAGE_FIELD_NUMBER: _ClassVar[int]
    FACT_FIELD_NUMBER: _ClassVar[int]
    FINDING_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_FIELD_NUMBER: _ClassVar[int]
    started: VariableFlowStarted
    usage: VariableUsage
    fact: VariableFlowFact
    finding: VariableFlowFinding
    completed: VariableFlowCompleted
    def __init__(self, started: _Optional[_Union[VariableFlowStarted, _Mapping]] = ..., usage: _Optional[_Union[VariableUsage, _Mapping]] = ..., fact: _Optional[_Union[VariableFlowFact, _Mapping]] = ..., finding: _Optional[_Union[VariableFlowFinding, _Mapping]] = ..., completed: _Optional[_Union[VariableFlowCompleted, _Mapping]] = ...) -> None: ...

class VariableFlowReport(_message.Message):
    __slots__ = ("analysis", "usages", "facts", "findings", "completed")
    ANALYSIS_FIELD_NUMBER: _ClassVar[int]
    USAGES_FIELD_NUMBER: _ClassVar[int]
    FACTS_FIELD_NUMBER: _ClassVar[int]
    FINDINGS_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_FIELD_NUMBER: _ClassVar[int]
    analysis: VariableFlowStarted
    usages: _containers.RepeatedCompositeFieldContainer[VariableUsage]
    facts: _containers.RepeatedCompositeFieldContainer[VariableFlowFact]
    findings: _containers.RepeatedCompositeFieldContainer[VariableFlowFinding]
    completed: VariableFlowCompleted
    def __init__(self, analysis: _Optional[_Union[VariableFlowStarted, _Mapping]] = ..., usages: _Optional[_Iterable[_Union[VariableUsage, _Mapping]]] = ..., facts: _Optional[_Iterable[_Union[VariableFlowFact, _Mapping]]] = ..., findings: _Optional[_Iterable[_Union[VariableFlowFinding, _Mapping]]] = ..., completed: _Optional[_Union[VariableFlowCompleted, _Mapping]] = ...) -> None: ...
