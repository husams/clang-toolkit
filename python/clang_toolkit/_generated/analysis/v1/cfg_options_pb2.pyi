from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class CfgOptions(_message.Message):
    __slots__ = ("prune_trivially_false_edges", "add_eh_edges", "add_initializers", "add_implicit_dtors", "add_temporary_dtors", "add_lifetime", "add_scopes", "add_loop_exit", "add_static_init_branches", "add_cxx_new_allocator", "add_cxx_default_init_expr_in_ctors", "add_cxx_default_init_expr_in_aggregates", "add_rich_cxx_constructors", "mark_elided_cxx_constructors", "add_virtual_base_branches", "omit_implicit_value_initializers", "assume_reachable_default_in_switch_statements", "always_add_statements")
    PRUNE_TRIVIALLY_FALSE_EDGES_FIELD_NUMBER: _ClassVar[int]
    ADD_EH_EDGES_FIELD_NUMBER: _ClassVar[int]
    ADD_INITIALIZERS_FIELD_NUMBER: _ClassVar[int]
    ADD_IMPLICIT_DTORS_FIELD_NUMBER: _ClassVar[int]
    ADD_TEMPORARY_DTORS_FIELD_NUMBER: _ClassVar[int]
    ADD_LIFETIME_FIELD_NUMBER: _ClassVar[int]
    ADD_SCOPES_FIELD_NUMBER: _ClassVar[int]
    ADD_LOOP_EXIT_FIELD_NUMBER: _ClassVar[int]
    ADD_STATIC_INIT_BRANCHES_FIELD_NUMBER: _ClassVar[int]
    ADD_CXX_NEW_ALLOCATOR_FIELD_NUMBER: _ClassVar[int]
    ADD_CXX_DEFAULT_INIT_EXPR_IN_CTORS_FIELD_NUMBER: _ClassVar[int]
    ADD_CXX_DEFAULT_INIT_EXPR_IN_AGGREGATES_FIELD_NUMBER: _ClassVar[int]
    ADD_RICH_CXX_CONSTRUCTORS_FIELD_NUMBER: _ClassVar[int]
    MARK_ELIDED_CXX_CONSTRUCTORS_FIELD_NUMBER: _ClassVar[int]
    ADD_VIRTUAL_BASE_BRANCHES_FIELD_NUMBER: _ClassVar[int]
    OMIT_IMPLICIT_VALUE_INITIALIZERS_FIELD_NUMBER: _ClassVar[int]
    ASSUME_REACHABLE_DEFAULT_IN_SWITCH_STATEMENTS_FIELD_NUMBER: _ClassVar[int]
    ALWAYS_ADD_STATEMENTS_FIELD_NUMBER: _ClassVar[int]
    prune_trivially_false_edges: bool
    add_eh_edges: bool
    add_initializers: bool
    add_implicit_dtors: bool
    add_temporary_dtors: bool
    add_lifetime: bool
    add_scopes: bool
    add_loop_exit: bool
    add_static_init_branches: bool
    add_cxx_new_allocator: bool
    add_cxx_default_init_expr_in_ctors: bool
    add_cxx_default_init_expr_in_aggregates: bool
    add_rich_cxx_constructors: bool
    mark_elided_cxx_constructors: bool
    add_virtual_base_branches: bool
    omit_implicit_value_initializers: bool
    assume_reachable_default_in_switch_statements: bool
    always_add_statements: bool
    def __init__(self, prune_trivially_false_edges: _Optional[bool] = ..., add_eh_edges: _Optional[bool] = ..., add_initializers: _Optional[bool] = ..., add_implicit_dtors: _Optional[bool] = ..., add_temporary_dtors: _Optional[bool] = ..., add_lifetime: _Optional[bool] = ..., add_scopes: _Optional[bool] = ..., add_loop_exit: _Optional[bool] = ..., add_static_init_branches: _Optional[bool] = ..., add_cxx_new_allocator: _Optional[bool] = ..., add_cxx_default_init_expr_in_ctors: _Optional[bool] = ..., add_cxx_default_init_expr_in_aggregates: _Optional[bool] = ..., add_rich_cxx_constructors: _Optional[bool] = ..., mark_elided_cxx_constructors: _Optional[bool] = ..., add_virtual_base_branches: _Optional[bool] = ..., omit_implicit_value_initializers: _Optional[bool] = ..., assume_reachable_default_in_switch_statements: _Optional[bool] = ..., always_add_statements: _Optional[bool] = ...) -> None: ...
