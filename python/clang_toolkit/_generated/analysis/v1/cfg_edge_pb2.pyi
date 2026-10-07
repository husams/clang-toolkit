from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class CfgEdge(_message.Message):
    __slots__ = ("reachable_block", "possibly_unreachable_block", "is_reachable")
    REACHABLE_BLOCK_FIELD_NUMBER: _ClassVar[int]
    POSSIBLY_UNREACHABLE_BLOCK_FIELD_NUMBER: _ClassVar[int]
    IS_REACHABLE_FIELD_NUMBER: _ClassVar[int]
    reachable_block: int
    possibly_unreachable_block: int
    is_reachable: bool
    def __init__(self, reachable_block: _Optional[int] = ..., possibly_unreachable_block: _Optional[int] = ..., is_reachable: _Optional[bool] = ...) -> None: ...
