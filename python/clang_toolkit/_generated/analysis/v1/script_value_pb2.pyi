from . import script_scalar_pb2 as _script_scalar_pb2
from . import script_match_rows_pb2 as _script_match_rows_pb2
from . import traverse_response_pb2 as _traverse_response_pb2
from . import cfg_response_pb2 as _cfg_response_pb2
from . import call_graph_response_pb2 as _call_graph_response_pb2
from . import script_tree_pb2 as _script_tree_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ScriptValue(_message.Message):
    __slots__ = ("scalar", "matches", "traversal", "cfg", "call_graph", "tree")
    SCALAR_FIELD_NUMBER: _ClassVar[int]
    MATCHES_FIELD_NUMBER: _ClassVar[int]
    TRAVERSAL_FIELD_NUMBER: _ClassVar[int]
    CFG_FIELD_NUMBER: _ClassVar[int]
    CALL_GRAPH_FIELD_NUMBER: _ClassVar[int]
    TREE_FIELD_NUMBER: _ClassVar[int]
    scalar: _script_scalar_pb2.ScriptScalar
    matches: _script_match_rows_pb2.ScriptMatchRows
    traversal: _traverse_response_pb2.TraverseResponse
    cfg: _cfg_response_pb2.CfgResponse
    call_graph: _call_graph_response_pb2.CallGraphResponse
    tree: _script_tree_pb2.ScriptTree
    def __init__(self, scalar: _Optional[_Union[_script_scalar_pb2.ScriptScalar, _Mapping]] = ..., matches: _Optional[_Union[_script_match_rows_pb2.ScriptMatchRows, _Mapping]] = ..., traversal: _Optional[_Union[_traverse_response_pb2.TraverseResponse, _Mapping]] = ..., cfg: _Optional[_Union[_cfg_response_pb2.CfgResponse, _Mapping]] = ..., call_graph: _Optional[_Union[_call_graph_response_pb2.CallGraphResponse, _Mapping]] = ..., tree: _Optional[_Union[_script_tree_pb2.ScriptTree, _Mapping]] = ...) -> None: ...
