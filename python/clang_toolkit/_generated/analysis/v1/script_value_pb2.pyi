from . import script_scalar_pb2 as _script_scalar_pb2
from . import script_match_rows_pb2 as _script_match_rows_pb2
from . import traverse_response_pb2 as _traverse_response_pb2
from . import cfg_response_pb2 as _cfg_response_pb2
from . import call_graph_response_pb2 as _call_graph_response_pb2
from . import script_tree_pb2 as _script_tree_pb2
from ...match.v1 import resources_pb2 as _resources_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ScriptValue(_message.Message):
    __slots__ = ("scalar", "matches", "traversal", "cfg", "call_graph", "tree", "list", "object", "files")
    SCALAR_FIELD_NUMBER: _ClassVar[int]
    MATCHES_FIELD_NUMBER: _ClassVar[int]
    TRAVERSAL_FIELD_NUMBER: _ClassVar[int]
    CFG_FIELD_NUMBER: _ClassVar[int]
    CALL_GRAPH_FIELD_NUMBER: _ClassVar[int]
    TREE_FIELD_NUMBER: _ClassVar[int]
    LIST_FIELD_NUMBER: _ClassVar[int]
    OBJECT_FIELD_NUMBER: _ClassVar[int]
    FILES_FIELD_NUMBER: _ClassVar[int]
    scalar: _script_scalar_pb2.ScriptScalar
    matches: _script_match_rows_pb2.ScriptMatchRows
    traversal: _traverse_response_pb2.TraverseResponse
    cfg: _cfg_response_pb2.CfgResponse
    call_graph: _call_graph_response_pb2.CallGraphResponse
    tree: _script_tree_pb2.ScriptTree
    list: ScriptList
    object: ScriptObject
    files: _resources_pb2.DiscoverFilesResponse
    def __init__(self, scalar: _Optional[_Union[_script_scalar_pb2.ScriptScalar, _Mapping]] = ..., matches: _Optional[_Union[_script_match_rows_pb2.ScriptMatchRows, _Mapping]] = ..., traversal: _Optional[_Union[_traverse_response_pb2.TraverseResponse, _Mapping]] = ..., cfg: _Optional[_Union[_cfg_response_pb2.CfgResponse, _Mapping]] = ..., call_graph: _Optional[_Union[_call_graph_response_pb2.CallGraphResponse, _Mapping]] = ..., tree: _Optional[_Union[_script_tree_pb2.ScriptTree, _Mapping]] = ..., list: _Optional[_Union[ScriptList, _Mapping]] = ..., object: _Optional[_Union[ScriptObject, _Mapping]] = ..., files: _Optional[_Union[_resources_pb2.DiscoverFilesResponse, _Mapping]] = ...) -> None: ...

class ScriptList(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedCompositeFieldContainer[ScriptValue]
    def __init__(self, values: _Optional[_Iterable[_Union[ScriptValue, _Mapping]]] = ...) -> None: ...

class ScriptObject(_message.Message):
    __slots__ = ("fields",)
    class FieldsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: ScriptValue
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[ScriptValue, _Mapping]] = ...) -> None: ...
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    fields: _containers.MessageMap[str, ScriptValue]
    def __init__(self, fields: _Optional[_Mapping[str, ScriptValue]] = ...) -> None: ...
