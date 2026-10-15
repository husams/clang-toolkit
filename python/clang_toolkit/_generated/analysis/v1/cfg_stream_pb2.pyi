from . import cfg_graph_pb2 as _cfg_graph_pb2
from . import cfg_block_pb2 as _cfg_block_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CfgStreamEvent(_message.Message):
    __slots__ = ("graph_started", "block", "graph_completed", "completed")
    GRAPH_STARTED_FIELD_NUMBER: _ClassVar[int]
    BLOCK_FIELD_NUMBER: _ClassVar[int]
    GRAPH_COMPLETED_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_FIELD_NUMBER: _ClassVar[int]
    graph_started: CfgGraphStarted
    block: CfgBlockEvent
    graph_completed: CfgGraphCompleted
    completed: CfgCompleted
    def __init__(self, graph_started: _Optional[_Union[CfgGraphStarted, _Mapping]] = ..., block: _Optional[_Union[CfgBlockEvent, _Mapping]] = ..., graph_completed: _Optional[_Union[CfgGraphCompleted, _Mapping]] = ..., completed: _Optional[_Union[CfgCompleted, _Mapping]] = ...) -> None: ...

class CfgGraphStarted(_message.Message):
    __slots__ = ("graph_index", "snapshot_generation", "graph")
    GRAPH_INDEX_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_GENERATION_FIELD_NUMBER: _ClassVar[int]
    GRAPH_FIELD_NUMBER: _ClassVar[int]
    graph_index: int
    snapshot_generation: int
    graph: _cfg_graph_pb2.CfgGraph
    def __init__(self, graph_index: _Optional[int] = ..., snapshot_generation: _Optional[int] = ..., graph: _Optional[_Union[_cfg_graph_pb2.CfgGraph, _Mapping]] = ...) -> None: ...

class CfgBlockEvent(_message.Message):
    __slots__ = ("graph_index", "block")
    GRAPH_INDEX_FIELD_NUMBER: _ClassVar[int]
    BLOCK_FIELD_NUMBER: _ClassVar[int]
    graph_index: int
    block: _cfg_block_pb2.CfgBlock
    def __init__(self, graph_index: _Optional[int] = ..., block: _Optional[_Union[_cfg_block_pb2.CfgBlock, _Mapping]] = ...) -> None: ...

class CfgGraphCompleted(_message.Message):
    __slots__ = ("graph_index", "block_count", "element_count", "is_complete")
    GRAPH_INDEX_FIELD_NUMBER: _ClassVar[int]
    BLOCK_COUNT_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_COUNT_FIELD_NUMBER: _ClassVar[int]
    IS_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    graph_index: int
    block_count: int
    element_count: int
    is_complete: bool
    def __init__(self, graph_index: _Optional[int] = ..., block_count: _Optional[int] = ..., element_count: _Optional[int] = ..., is_complete: _Optional[bool] = ...) -> None: ...

class CfgCompleted(_message.Message):
    __slots__ = ("graph_count", "block_count", "element_count")
    GRAPH_COUNT_FIELD_NUMBER: _ClassVar[int]
    BLOCK_COUNT_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_COUNT_FIELD_NUMBER: _ClassVar[int]
    graph_count: int
    block_count: int
    element_count: int
    def __init__(self, graph_count: _Optional[int] = ..., block_count: _Optional[int] = ..., element_count: _Optional[int] = ...) -> None: ...
