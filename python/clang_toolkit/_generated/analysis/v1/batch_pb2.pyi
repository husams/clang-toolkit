from ...match.v1 import resources_pb2 as _resources_pb2
from . import script_response_pb2 as _script_response_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class StartBatchRequest(_message.Message):
    __slots__ = ("request_id", "inputs", "body_source", "group_variable", "size", "count", "jobs", "memory_bytes", "continue_on_error")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    INPUTS_FIELD_NUMBER: _ClassVar[int]
    BODY_SOURCE_FIELD_NUMBER: _ClassVar[int]
    GROUP_VARIABLE_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    JOBS_FIELD_NUMBER: _ClassVar[int]
    MEMORY_BYTES_FIELD_NUMBER: _ClassVar[int]
    CONTINUE_ON_ERROR_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    inputs: _containers.RepeatedCompositeFieldContainer[_resources_pb2.InputDescriptor]
    body_source: str
    group_variable: str
    size: int
    count: int
    jobs: int
    memory_bytes: int
    continue_on_error: bool
    def __init__(self, request_id: _Optional[str] = ..., inputs: _Optional[_Iterable[_Union[_resources_pb2.InputDescriptor, _Mapping]]] = ..., body_source: _Optional[str] = ..., group_variable: _Optional[str] = ..., size: _Optional[int] = ..., count: _Optional[int] = ..., jobs: _Optional[int] = ..., memory_bytes: _Optional[int] = ..., continue_on_error: _Optional[bool] = ...) -> None: ...

class BatchRunRequest(_message.Message):
    __slots__ = ("run_id",)
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    def __init__(self, run_id: _Optional[str] = ...) -> None: ...

class BatchControlRequest(_message.Message):
    __slots__ = ("run_id", "expected_revision")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_REVISION_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    expected_revision: int
    def __init__(self, run_id: _Optional[str] = ..., expected_revision: _Optional[int] = ...) -> None: ...

class BatchExport(_message.Message):
    __slots__ = ("path", "digest", "state")
    PATH_FIELD_NUMBER: _ClassVar[int]
    DIGEST_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    path: str
    digest: str
    state: str
    def __init__(self, path: _Optional[str] = ..., digest: _Optional[str] = ..., state: _Optional[str] = ...) -> None: ...

class BatchGroup(_message.Message):
    __slots__ = ("index", "inputs", "source_revisions", "state", "message", "resource_scope_id", "cleanup_acknowledged", "result", "exports")
    INDEX_FIELD_NUMBER: _ClassVar[int]
    INPUTS_FIELD_NUMBER: _ClassVar[int]
    SOURCE_REVISIONS_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_SCOPE_ID_FIELD_NUMBER: _ClassVar[int]
    CLEANUP_ACKNOWLEDGED_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    EXPORTS_FIELD_NUMBER: _ClassVar[int]
    index: int
    inputs: _containers.RepeatedCompositeFieldContainer[_resources_pb2.InputDescriptor]
    source_revisions: _containers.RepeatedScalarFieldContainer[str]
    state: str
    message: str
    resource_scope_id: str
    cleanup_acknowledged: bool
    result: _script_response_pb2.ScriptResponse
    exports: _containers.RepeatedCompositeFieldContainer[BatchExport]
    def __init__(self, index: _Optional[int] = ..., inputs: _Optional[_Iterable[_Union[_resources_pb2.InputDescriptor, _Mapping]]] = ..., source_revisions: _Optional[_Iterable[str]] = ..., state: _Optional[str] = ..., message: _Optional[str] = ..., resource_scope_id: _Optional[str] = ..., cleanup_acknowledged: _Optional[bool] = ..., result: _Optional[_Union[_script_response_pb2.ScriptResponse, _Mapping]] = ..., exports: _Optional[_Iterable[_Union[BatchExport, _Mapping]]] = ...) -> None: ...

class BatchRun(_message.Message):
    __slots__ = ("run_id", "revision", "state", "groups", "results_complete", "peak_accounted_bytes", "peak_reserved_bytes", "manifest")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    REVISION_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    GROUPS_FIELD_NUMBER: _ClassVar[int]
    RESULTS_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    PEAK_ACCOUNTED_BYTES_FIELD_NUMBER: _ClassVar[int]
    PEAK_RESERVED_BYTES_FIELD_NUMBER: _ClassVar[int]
    MANIFEST_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    revision: int
    state: str
    groups: _containers.RepeatedCompositeFieldContainer[BatchGroup]
    results_complete: bool
    peak_accounted_bytes: int
    peak_reserved_bytes: int
    manifest: StartBatchRequest
    def __init__(self, run_id: _Optional[str] = ..., revision: _Optional[int] = ..., state: _Optional[str] = ..., groups: _Optional[_Iterable[_Union[BatchGroup, _Mapping]]] = ..., results_complete: _Optional[bool] = ..., peak_accounted_bytes: _Optional[int] = ..., peak_reserved_bytes: _Optional[int] = ..., manifest: _Optional[_Union[StartBatchRequest, _Mapping]] = ...) -> None: ...
