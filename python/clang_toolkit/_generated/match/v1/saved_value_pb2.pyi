from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SavedValue(_message.Message):
    __slots__ = ("schema_version", "envelope")
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    ENVELOPE_FIELD_NUMBER: _ClassVar[int]
    schema_version: int
    envelope: SavedData
    def __init__(self, schema_version: _Optional[int] = ..., envelope: _Optional[_Union[SavedData, _Mapping]] = ...) -> None: ...

class SavedData(_message.Message):
    __slots__ = ("null_value", "bool_value", "integer_value", "float_value", "string_value", "list_value", "record_value")
    class Null(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        NULL_VALUE: _ClassVar[SavedData.Null]
    NULL_VALUE: SavedData.Null
    NULL_VALUE_FIELD_NUMBER: _ClassVar[int]
    BOOL_VALUE_FIELD_NUMBER: _ClassVar[int]
    INTEGER_VALUE_FIELD_NUMBER: _ClassVar[int]
    FLOAT_VALUE_FIELD_NUMBER: _ClassVar[int]
    STRING_VALUE_FIELD_NUMBER: _ClassVar[int]
    LIST_VALUE_FIELD_NUMBER: _ClassVar[int]
    RECORD_VALUE_FIELD_NUMBER: _ClassVar[int]
    null_value: SavedData.Null
    bool_value: bool
    integer_value: str
    float_value: float
    string_value: str
    list_value: SavedList
    record_value: SavedRecord
    def __init__(self, null_value: _Optional[_Union[SavedData.Null, str]] = ..., bool_value: _Optional[bool] = ..., integer_value: _Optional[str] = ..., float_value: _Optional[float] = ..., string_value: _Optional[str] = ..., list_value: _Optional[_Union[SavedList, _Mapping]] = ..., record_value: _Optional[_Union[SavedRecord, _Mapping]] = ...) -> None: ...

class SavedList(_message.Message):
    __slots__ = ("items",)
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedCompositeFieldContainer[SavedData]
    def __init__(self, items: _Optional[_Iterable[_Union[SavedData, _Mapping]]] = ...) -> None: ...

class SavedRecord(_message.Message):
    __slots__ = ("fields",)
    class FieldsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: SavedData
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[SavedData, _Mapping]] = ...) -> None: ...
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    fields: _containers.MessageMap[str, SavedData]
    def __init__(self, fields: _Optional[_Mapping[str, SavedData]] = ...) -> None: ...
