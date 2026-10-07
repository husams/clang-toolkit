from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class ParseRequest(_message.Message):
    __slots__ = ("file_path", "compile_arguments", "working_directory")
    FILE_PATH_FIELD_NUMBER: _ClassVar[int]
    COMPILE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    WORKING_DIRECTORY_FIELD_NUMBER: _ClassVar[int]
    file_path: str
    compile_arguments: _containers.RepeatedScalarFieldContainer[str]
    working_directory: str
    def __init__(self, file_path: _Optional[str] = ..., compile_arguments: _Optional[_Iterable[str]] = ..., working_directory: _Optional[str] = ...) -> None: ...
