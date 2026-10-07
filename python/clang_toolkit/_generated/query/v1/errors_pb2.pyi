from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class LimitViolation(_message.Message):
    __slots__ = ("limit_name", "current_value", "configured_limit", "requested_increment", "projected_value")
    LIMIT_NAME_FIELD_NUMBER: _ClassVar[int]
    CURRENT_VALUE_FIELD_NUMBER: _ClassVar[int]
    CONFIGURED_LIMIT_FIELD_NUMBER: _ClassVar[int]
    REQUESTED_INCREMENT_FIELD_NUMBER: _ClassVar[int]
    PROJECTED_VALUE_FIELD_NUMBER: _ClassVar[int]
    limit_name: str
    current_value: int
    configured_limit: int
    requested_increment: int
    projected_value: int
    def __init__(self, limit_name: _Optional[str] = ..., current_value: _Optional[int] = ..., configured_limit: _Optional[int] = ..., requested_increment: _Optional[int] = ..., projected_value: _Optional[int] = ...) -> None: ...

class Rejected(_message.Message):
    __slots__ = ("code", "message", "violations")
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    VIOLATIONS_FIELD_NUMBER: _ClassVar[int]
    code: str
    message: str
    violations: _containers.RepeatedCompositeFieldContainer[LimitViolation]
    def __init__(self, code: _Optional[str] = ..., message: _Optional[str] = ..., violations: _Optional[_Iterable[_Union[LimitViolation, _Mapping]]] = ...) -> None: ...
