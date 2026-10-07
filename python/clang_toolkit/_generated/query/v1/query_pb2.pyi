from . import commands_pb2 as _commands_pb2  # noqa: E402, F401
from . import errors_pb2 as _errors_pb2  # noqa: E402, F401
from . import events_pb2 as _events_pb2  # noqa: E402, F401
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional
from .commands_pb2 import FileInput as FileInput
from .commands_pb2 import QueryRequest as QueryRequest
from .commands_pb2 import StartQuery as StartQuery
from .commands_pb2 import AddFiles as AddFiles
from .commands_pb2 import Match as Match
from .commands_pb2 import Pause as Pause
from .commands_pb2 import Resume as Resume
from .commands_pb2 import QueryCommand as QueryCommand
from .errors_pb2 import LimitViolation as LimitViolation
from .errors_pb2 import Rejected as Rejected
from .events_pb2 import Queued as Queued
from .events_pb2 import Started as Started
from .events_pb2 import Progress as Progress
from .events_pb2 import SemanticBinding as SemanticBinding
from .events_pb2 import MatchEvent as MatchEvent
from .events_pb2 import Completed as Completed
from .events_pb2 import Control as Control
from .events_pb2 import QueryEvent as QueryEvent

DESCRIPTOR: _descriptor.FileDescriptor

class VersionRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VersionResponse(_message.Message):
    __slots__ = ("version", "revision")
    VERSION_FIELD_NUMBER: _ClassVar[int]
    REVISION_FIELD_NUMBER: _ClassVar[int]
    version: str
    revision: str
    def __init__(self, version: _Optional[str] = ..., revision: _Optional[str] = ...) -> None: ...
