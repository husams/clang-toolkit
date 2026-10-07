from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class FieldState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FIELD_STATE_UNSPECIFIED: _ClassVar[FieldState]
    FIELD_STATE_PRESENT: _ClassVar[FieldState]
    FIELD_STATE_SEMANTICALLY_ABSENT: _ClassVar[FieldState]
    FIELD_STATE_UNREQUESTED: _ClassVar[FieldState]
    FIELD_STATE_INAPPLICABLE: _ClassVar[FieldState]
    FIELD_STATE_UNAVAILABLE: _ClassVar[FieldState]
    FIELD_STATE_TRUNCATED: _ClassVar[FieldState]

class AccessSpecifier(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ACCESS_SPECIFIER_UNSPECIFIED: _ClassVar[AccessSpecifier]
    ACCESS_SPECIFIER_NONE: _ClassVar[AccessSpecifier]
    ACCESS_SPECIFIER_PUBLIC: _ClassVar[AccessSpecifier]
    ACCESS_SPECIFIER_PROTECTED: _ClassVar[AccessSpecifier]
    ACCESS_SPECIFIER_PRIVATE: _ClassVar[AccessSpecifier]

class ValueCategory(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    VALUE_CATEGORY_UNSPECIFIED: _ClassVar[ValueCategory]
    VALUE_CATEGORY_PRVALUE: _ClassVar[ValueCategory]
    VALUE_CATEGORY_LVALUE: _ClassVar[ValueCategory]
    VALUE_CATEGORY_XVALUE: _ClassVar[ValueCategory]

class ObjectKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    OBJECT_KIND_UNSPECIFIED: _ClassVar[ObjectKind]
    OBJECT_KIND_ORDINARY: _ClassVar[ObjectKind]
    OBJECT_KIND_BIT_FIELD: _ClassVar[ObjectKind]
    OBJECT_KIND_VECTOR_COMPONENT: _ClassVar[ObjectKind]
    OBJECT_KIND_MATRIX_COMPONENT: _ClassVar[ObjectKind]

class RefQualifier(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    REF_QUALIFIER_UNSPECIFIED: _ClassVar[RefQualifier]
    REF_QUALIFIER_NONE: _ClassVar[RefQualifier]
    REF_QUALIFIER_LVALUE: _ClassVar[RefQualifier]
    REF_QUALIFIER_RVALUE: _ClassVar[RefQualifier]

class StorageClass(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    STORAGE_CLASS_UNSPECIFIED: _ClassVar[StorageClass]
    STORAGE_CLASS_NONE: _ClassVar[StorageClass]
    STORAGE_CLASS_EXTERN: _ClassVar[StorageClass]
    STORAGE_CLASS_STATIC: _ClassVar[StorageClass]
    STORAGE_CLASS_PRIVATE_EXTERN: _ClassVar[StorageClass]
    STORAGE_CLASS_AUTO: _ClassVar[StorageClass]
    STORAGE_CLASS_REGISTER: _ClassVar[StorageClass]

class ConstructionKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CONSTRUCTION_KIND_UNSPECIFIED: _ClassVar[ConstructionKind]
    CONSTRUCTION_KIND_COMPLETE_OBJECT: _ClassVar[ConstructionKind]
    CONSTRUCTION_KIND_NONVIRTUAL_BASE: _ClassVar[ConstructionKind]
    CONSTRUCTION_KIND_VIRTUAL_BASE: _ClassVar[ConstructionKind]
    CONSTRUCTION_KIND_DELEGATING: _ClassVar[ConstructionKind]

class TagKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TAG_KIND_UNSPECIFIED: _ClassVar[TagKind]
    TAG_KIND_STRUCT: _ClassVar[TagKind]
    TAG_KIND_UNION: _ClassVar[TagKind]
    TAG_KIND_CLASS: _ClassVar[TagKind]
    TAG_KIND_ENUM: _ClassVar[TagKind]
    TAG_KIND_INTERFACE: _ClassVar[TagKind]
FIELD_STATE_UNSPECIFIED: FieldState
FIELD_STATE_PRESENT: FieldState
FIELD_STATE_SEMANTICALLY_ABSENT: FieldState
FIELD_STATE_UNREQUESTED: FieldState
FIELD_STATE_INAPPLICABLE: FieldState
FIELD_STATE_UNAVAILABLE: FieldState
FIELD_STATE_TRUNCATED: FieldState
ACCESS_SPECIFIER_UNSPECIFIED: AccessSpecifier
ACCESS_SPECIFIER_NONE: AccessSpecifier
ACCESS_SPECIFIER_PUBLIC: AccessSpecifier
ACCESS_SPECIFIER_PROTECTED: AccessSpecifier
ACCESS_SPECIFIER_PRIVATE: AccessSpecifier
VALUE_CATEGORY_UNSPECIFIED: ValueCategory
VALUE_CATEGORY_PRVALUE: ValueCategory
VALUE_CATEGORY_LVALUE: ValueCategory
VALUE_CATEGORY_XVALUE: ValueCategory
OBJECT_KIND_UNSPECIFIED: ObjectKind
OBJECT_KIND_ORDINARY: ObjectKind
OBJECT_KIND_BIT_FIELD: ObjectKind
OBJECT_KIND_VECTOR_COMPONENT: ObjectKind
OBJECT_KIND_MATRIX_COMPONENT: ObjectKind
REF_QUALIFIER_UNSPECIFIED: RefQualifier
REF_QUALIFIER_NONE: RefQualifier
REF_QUALIFIER_LVALUE: RefQualifier
REF_QUALIFIER_RVALUE: RefQualifier
STORAGE_CLASS_UNSPECIFIED: StorageClass
STORAGE_CLASS_NONE: StorageClass
STORAGE_CLASS_EXTERN: StorageClass
STORAGE_CLASS_STATIC: StorageClass
STORAGE_CLASS_PRIVATE_EXTERN: StorageClass
STORAGE_CLASS_AUTO: StorageClass
STORAGE_CLASS_REGISTER: StorageClass
CONSTRUCTION_KIND_UNSPECIFIED: ConstructionKind
CONSTRUCTION_KIND_COMPLETE_OBJECT: ConstructionKind
CONSTRUCTION_KIND_NONVIRTUAL_BASE: ConstructionKind
CONSTRUCTION_KIND_VIRTUAL_BASE: ConstructionKind
CONSTRUCTION_KIND_DELEGATING: ConstructionKind
TAG_KIND_UNSPECIFIED: TagKind
TAG_KIND_STRUCT: TagKind
TAG_KIND_UNION: TagKind
TAG_KIND_CLASS: TagKind
TAG_KIND_ENUM: TagKind
TAG_KIND_INTERFACE: TagKind

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class AddressSpace(_message.Message):
    __slots__ = ("default_space", "target_space", "language_space")
    DEFAULT_SPACE_FIELD_NUMBER: _ClassVar[int]
    TARGET_SPACE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_SPACE_FIELD_NUMBER: _ClassVar[int]
    default_space: Empty
    target_space: int
    language_space: str
    def __init__(self, default_space: _Optional[_Union[Empty, _Mapping]] = ..., target_space: _Optional[int] = ..., language_space: _Optional[str] = ...) -> None: ...

class Qualifiers(_message.Message):
    __slots__ = ("is_const", "is_volatile", "is_restrict", "is_unaligned", "address_space")
    IS_CONST_FIELD_NUMBER: _ClassVar[int]
    IS_VOLATILE_FIELD_NUMBER: _ClassVar[int]
    IS_RESTRICT_FIELD_NUMBER: _ClassVar[int]
    IS_UNALIGNED_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_SPACE_FIELD_NUMBER: _ClassVar[int]
    is_const: bool
    is_volatile: bool
    is_restrict: bool
    is_unaligned: bool
    address_space: AddressSpace
    def __init__(self, is_const: _Optional[bool] = ..., is_volatile: _Optional[bool] = ..., is_restrict: _Optional[bool] = ..., is_unaligned: _Optional[bool] = ..., address_space: _Optional[_Union[AddressSpace, _Mapping]] = ...) -> None: ...

class FieldAvailability(_message.Message):
    __slots__ = ("field_path", "state", "reason")
    FIELD_PATH_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    field_path: str
    state: FieldState
    reason: str
    def __init__(self, field_path: _Optional[str] = ..., state: _Optional[_Union[FieldState, str]] = ..., reason: _Optional[str] = ...) -> None: ...
