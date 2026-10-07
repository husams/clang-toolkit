from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class FileInput(_message.Message):
    __slots__ = ("path", "compile_arguments", "working_directory", "compilation_database")
    PATH_FIELD_NUMBER: _ClassVar[int]
    COMPILE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    WORKING_DIRECTORY_FIELD_NUMBER: _ClassVar[int]
    COMPILATION_DATABASE_FIELD_NUMBER: _ClassVar[int]
    path: str
    compile_arguments: _containers.RepeatedScalarFieldContainer[str]
    working_directory: str
    compilation_database: str
    def __init__(self, path: _Optional[str] = ..., compile_arguments: _Optional[_Iterable[str]] = ..., working_directory: _Optional[str] = ..., compilation_database: _Optional[str] = ...) -> None: ...

class QueryRequest(_message.Message):
    __slots__ = ("query", "files")
    QUERY_FIELD_NUMBER: _ClassVar[int]
    FILES_FIELD_NUMBER: _ClassVar[int]
    query: str
    files: _containers.RepeatedCompositeFieldContainer[FileInput]
    def __init__(self, query: _Optional[str] = ..., files: _Optional[_Iterable[_Union[FileInput, _Mapping]]] = ...) -> None: ...

class StartQuery(_message.Message):
    __slots__ = ("query",)
    QUERY_FIELD_NUMBER: _ClassVar[int]
    query: str
    def __init__(self, query: _Optional[str] = ...) -> None: ...

class AddFiles(_message.Message):
    __slots__ = ("files",)
    FILES_FIELD_NUMBER: _ClassVar[int]
    files: _containers.RepeatedCompositeFieldContainer[FileInput]
    def __init__(self, files: _Optional[_Iterable[_Union[FileInput, _Mapping]]] = ...) -> None: ...

class Match(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Pause(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Resume(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class QueryCommand(_message.Message):
    __slots__ = ("request_id", "start_query", "add_files", "match", "pause", "resume")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    START_QUERY_FIELD_NUMBER: _ClassVar[int]
    ADD_FILES_FIELD_NUMBER: _ClassVar[int]
    MATCH_FIELD_NUMBER: _ClassVar[int]
    PAUSE_FIELD_NUMBER: _ClassVar[int]
    RESUME_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    start_query: StartQuery
    add_files: AddFiles
    match: Match
    pause: Pause
    resume: Resume
    def __init__(self, request_id: _Optional[str] = ..., start_query: _Optional[_Union[StartQuery, _Mapping]] = ..., add_files: _Optional[_Union[AddFiles, _Mapping]] = ..., match: _Optional[_Union[Match, _Mapping]] = ..., pause: _Optional[_Union[Pause, _Mapping]] = ..., resume: _Optional[_Union[Resume, _Mapping]] = ...) -> None: ...
