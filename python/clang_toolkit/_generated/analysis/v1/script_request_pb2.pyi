from ...match.v1 import match_service_pb2 as _match_service_pb2
from . import script_compilation_profile_pb2 as _script_compilation_profile_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ScriptRequest(_message.Message):
    __slots__ = ("file", "source", "max_steps", "profile", "resource_scope_id")
    FILE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    MAX_STEPS_FIELD_NUMBER: _ClassVar[int]
    PROFILE_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_SCOPE_ID_FIELD_NUMBER: _ClassVar[int]
    file: _match_service_pb2.FileMatchTarget
    source: str
    max_steps: int
    profile: _script_compilation_profile_pb2.ScriptCompilationProfile
    resource_scope_id: str
    def __init__(self, file: _Optional[_Union[_match_service_pb2.FileMatchTarget, _Mapping]] = ..., source: _Optional[str] = ..., max_steps: _Optional[int] = ..., profile: _Optional[_Union[_script_compilation_profile_pb2.ScriptCompilationProfile, _Mapping]] = ..., resource_scope_id: _Optional[str] = ...) -> None: ...
