from . import cfg_graph_pb2 as _cfg_graph_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CfgResponse(_message.Message):
    __slots__ = ("graphs",)
    GRAPHS_FIELD_NUMBER: _ClassVar[int]
    graphs: _containers.RepeatedCompositeFieldContainer[_cfg_graph_pb2.CfgGraph]
    def __init__(self, graphs: _Optional[_Iterable[_Union[_cfg_graph_pb2.CfgGraph, _Mapping]]] = ...) -> None: ...
