from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class ScriptScalar(_message.Message):
    __slots__ = ("text", "integer", "number", "boolean")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    INTEGER_FIELD_NUMBER: _ClassVar[int]
    NUMBER_FIELD_NUMBER: _ClassVar[int]
    BOOLEAN_FIELD_NUMBER: _ClassVar[int]
    text: str
    integer: int
    number: float
    boolean: bool
    def __init__(self, text: _Optional[str] = ..., integer: _Optional[int] = ..., number: _Optional[float] = ..., boolean: _Optional[bool] = ...) -> None: ...
