from ...match.v1 import match_service_pb2 as _match_service_pb2
from . import cfg_options_pb2 as _cfg_options_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CfgRequest(_message.Message):
    __slots__ = ("file", "function", "options", "max_functions", "max_blocks", "max_elements")
    FILE_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    MAX_FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    MAX_BLOCKS_FIELD_NUMBER: _ClassVar[int]
    MAX_ELEMENTS_FIELD_NUMBER: _ClassVar[int]
    file: _match_service_pb2.FileMatchTarget
    function: str
    options: _cfg_options_pb2.CfgOptions
    max_functions: int
    max_blocks: int
    max_elements: int
    def __init__(self, file: _Optional[_Union[_match_service_pb2.FileMatchTarget, _Mapping]] = ..., function: _Optional[str] = ..., options: _Optional[_Union[_cfg_options_pb2.CfgOptions, _Mapping]] = ..., max_functions: _Optional[int] = ..., max_blocks: _Optional[int] = ..., max_elements: _Optional[int] = ...) -> None: ...
