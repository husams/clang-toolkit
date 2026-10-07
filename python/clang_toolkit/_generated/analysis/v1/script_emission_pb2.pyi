from . import script_value_pb2 as _script_value_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ScriptEmission(_message.Message):
    __slots__ = ("name", "value")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    name: str
    value: _script_value_pb2.ScriptValue
    def __init__(self, name: _Optional[str] = ..., value: _Optional[_Union[_script_value_pb2.ScriptValue, _Mapping]] = ...) -> None: ...
