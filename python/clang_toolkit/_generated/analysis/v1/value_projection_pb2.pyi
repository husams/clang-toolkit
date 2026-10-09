from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ValueProjection(_message.Message):
    __slots__ = ("mode", "max_depth", "max_nodes")
    class Mode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        MODE_UNSPECIFIED: _ClassVar[ValueProjection.Mode]
        SHALLOW: _ClassVar[ValueProjection.Mode]
        RECURSIVE: _ClassVar[ValueProjection.Mode]
    MODE_UNSPECIFIED: ValueProjection.Mode
    SHALLOW: ValueProjection.Mode
    RECURSIVE: ValueProjection.Mode
    MODE_FIELD_NUMBER: _ClassVar[int]
    MAX_DEPTH_FIELD_NUMBER: _ClassVar[int]
    MAX_NODES_FIELD_NUMBER: _ClassVar[int]
    mode: ValueProjection.Mode
    max_depth: int
    max_nodes: int
    def __init__(self, mode: _Optional[_Union[ValueProjection.Mode, str]] = ..., max_depth: _Optional[int] = ..., max_nodes: _Optional[int] = ...) -> None: ...
