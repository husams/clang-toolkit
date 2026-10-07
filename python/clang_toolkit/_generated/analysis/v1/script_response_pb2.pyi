from . import script_emission_pb2 as _script_emission_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ScriptResponse(_message.Message):
    __slots__ = ("emissions", "executed_steps")
    EMISSIONS_FIELD_NUMBER: _ClassVar[int]
    EXECUTED_STEPS_FIELD_NUMBER: _ClassVar[int]
    emissions: _containers.RepeatedCompositeFieldContainer[_script_emission_pb2.ScriptEmission]
    executed_steps: int
    def __init__(self, emissions: _Optional[_Iterable[_Union[_script_emission_pb2.ScriptEmission, _Mapping]]] = ..., executed_steps: _Optional[int] = ...) -> None: ...
