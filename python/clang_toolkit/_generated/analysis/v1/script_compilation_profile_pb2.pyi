from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class ScriptCompilationProfile(_message.Message):
    __slots__ = ("working_directory", "compile_arguments", "compilation_database", "frozen", "expected_profile_id")
    WORKING_DIRECTORY_FIELD_NUMBER: _ClassVar[int]
    COMPILE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    COMPILATION_DATABASE_FIELD_NUMBER: _ClassVar[int]
    FROZEN_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_PROFILE_ID_FIELD_NUMBER: _ClassVar[int]
    working_directory: str
    compile_arguments: _containers.RepeatedScalarFieldContainer[str]
    compilation_database: str
    frozen: bool
    expected_profile_id: str
    def __init__(self, working_directory: _Optional[str] = ..., compile_arguments: _Optional[_Iterable[str]] = ..., compilation_database: _Optional[str] = ..., frozen: _Optional[bool] = ..., expected_profile_id: _Optional[str] = ...) -> None: ...
