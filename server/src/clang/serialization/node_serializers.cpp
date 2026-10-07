#include "node_serializers.hpp"
#include "decl/access_spec_decl.hpp"
#include "decl/binding_decl.hpp"
#include "decl/block_decl.hpp"
#include "decl/builtin_template_decl.hpp"
#include "decl/class_template_decl.hpp"
#include "decl/class_template_partial_specialization_decl.hpp"
#include "decl/class_template_specialization_decl.hpp"
#include "decl/concept_decl.hpp"
#include "decl/constructor_using_shadow_decl.hpp"
#include "decl/cxx_constructor_decl.hpp"
#include "decl/cxx_conversion_decl.hpp"
#include "decl/cxx_deduction_guide_decl.hpp"
#include "decl/cxx_destructor_decl.hpp"
#include "decl/cxx_method_decl.hpp"
#include "decl/cxx_record_decl.hpp"
#include "decl/decomposition_decl.hpp"
#include "decl/empty_decl.hpp"
#include "decl/enum_constant_decl.hpp"
#include "decl/enum_decl.hpp"
#include "decl/export_decl.hpp"
#include "decl/extern_c_context_decl.hpp"
#include "decl/field_decl.hpp"
#include "decl/file_scope_asm_decl.hpp"
#include "decl/friend_decl.hpp"
#include "decl/friend_template_decl.hpp"
#include "decl/function_decl.hpp"
#include "decl/function_template_decl.hpp"
#include "decl/implicit_concept_specialization_decl.hpp"
#include "decl/implicit_param_decl.hpp"
#include "decl/import_decl.hpp"
#include "decl/indirect_field_decl.hpp"
#include "decl/label_decl.hpp"
#include "decl/lifetime_extended_temporary_decl.hpp"
#include "decl/linkage_spec_decl.hpp"
#include "decl/ms_guid_decl.hpp"
#include "decl/ms_property_decl.hpp"
#include "decl/namespace_alias_decl.hpp"
#include "decl/namespace_decl.hpp"
#include "decl/non_type_template_parm_decl.hpp"
#include "decl/parm_var_decl.hpp"
#include "decl/pragma_comment_decl.hpp"
#include "decl/pragma_detect_mismatch_decl.hpp"
#include "decl/record_decl.hpp"
#include "decl/requires_expr_body_decl.hpp"
#include "decl/static_assert_decl.hpp"
#include "decl/template_param_object_decl.hpp"
#include "decl/template_template_parm_decl.hpp"
#include "decl/template_type_parm_decl.hpp"
#include "decl/top_level_stmt_decl.hpp"
#include "decl/translation_unit_decl.hpp"
#include "decl/type_alias_decl.hpp"
#include "decl/type_alias_template_decl.hpp"
#include "decl/typedef_decl.hpp"
#include "decl/unnamed_global_constant_decl.hpp"
#include "decl/unresolved_using_if_exists_decl.hpp"
#include "decl/unresolved_using_typename_decl.hpp"
#include "decl/unresolved_using_value_decl.hpp"
#include "decl/using_decl.hpp"
#include "decl/using_directive_decl.hpp"
#include "decl/using_enum_decl.hpp"
#include "decl/using_pack_decl.hpp"
#include "decl/using_shadow_decl.hpp"
#include "decl/var_decl.hpp"
#include "decl/var_template_decl.hpp"
#include "decl/var_template_partial_specialization_decl.hpp"
#include "decl/var_template_specialization_decl.hpp"
#include "expr/matrix_subscript_expr.hpp"
#include "expr/member_expr.hpp"
#include "expr/no_init_expr.hpp"
#include "expr/offset_of_expr.hpp"
#include "expr/opaque_value_expr.hpp"
#include "expr/pack_expansion_expr.hpp"
#include "expr/pack_indexing_expr.hpp"
#include "expr/paren_expr.hpp"
#include "expr/paren_list_expr.hpp"
#include "expr/predefined_expr.hpp"
#include "expr/pseudo_object_expr.hpp"
#include "expr/recovery_expr.hpp"
#include "expr/requires_expr.hpp"
#include "expr/shuffle_vector_expr.hpp"
#include "expr/size_of_pack_expr.hpp"
#include "expr/source_loc_expr.hpp"
#include "expr/stmt_expr.hpp"
#include "expr/string_literal.hpp"
#include "expr/subst_non_type_template_parm_expr.hpp"
#include "expr/subst_non_type_template_parm_pack_expr.hpp"
#include "expr/type_trait_expr.hpp"
#include "expr/unary_expr_or_type_trait_expr.hpp"
#include "expr/unary_operator.hpp"
#include "expr/unresolved_lookup_expr.hpp"
#include "expr/unresolved_member_expr.hpp"
#include "expr/va_arg_expr.hpp"
#include "semantic_helpers.hpp"
#include "stmt/attributed_stmt.hpp"
#include "stmt/break_stmt.hpp"
#include "stmt/case_stmt.hpp"
#include "stmt/compound_stmt.hpp"
#include "stmt/continue_stmt.hpp"
#include "stmt/coreturn_stmt.hpp"
#include "stmt/coroutine_body_stmt.hpp"
#include "stmt/cxx_catch_stmt.hpp"
#include "stmt/cxx_for_range_stmt.hpp"
#include "stmt/cxx_try_stmt.hpp"
#include "stmt/decl_stmt.hpp"
#include "stmt/default_stmt.hpp"
#include "stmt/do_stmt.hpp"
#include "stmt/for_stmt.hpp"
#include "stmt/gcc_asm_stmt.hpp"
#include "stmt/goto_stmt.hpp"
#include "stmt/if_stmt.hpp"
#include "stmt/indirect_goto_stmt.hpp"
#include "stmt/label_stmt.hpp"
#include "stmt/ms_asm_stmt.hpp"
#include "stmt/ms_dependent_exists_stmt.hpp"
#include "stmt/null_stmt.hpp"
#include "stmt/return_stmt.hpp"
#include "stmt/seh_except_stmt.hpp"
#include "stmt/seh_finally_stmt.hpp"
#include "stmt/seh_leave_stmt.hpp"
#include "stmt/seh_try_stmt.hpp"
#include "stmt/switch_stmt.hpp"
#include "stmt/while_stmt.hpp"
#if CLANG_VERSION_MAJOR >= 22
#include "expr/matrix_single_subscript_expr.hpp"
#endif
#include "expr/addr_label_expr.hpp"
#include "expr/array_init_index_expr.hpp"
#include "expr/array_init_loop_expr.hpp"
#include "expr/array_subscript_expr.hpp"
#include "expr/array_type_trait_expr.hpp"
#include "expr/atomic_expr.hpp"
#include "expr/binary_conditional_operator.hpp"
#include "expr/binary_operator.hpp"
#include "expr/block_expr.hpp"
#include "expr/builtin_bit_cast_expr.hpp"
#include "expr/c_style_cast_expr.hpp"
#include "expr/call_expr.hpp"
#include "expr/character_literal.hpp"
#include "expr/choose_expr.hpp"
#include "expr/coawait_expr.hpp"
#include "expr/compound_assign_operator.hpp"
#include "expr/compound_literal_expr.hpp"
#include "expr/concept_specialization_expr.hpp"
#include "expr/conditional_operator.hpp"
#include "expr/constant_expr.hpp"
#include "expr/convert_vector_expr.hpp"
#include "expr/coyield_expr.hpp"
#include "expr/cxx_addrspace_cast_expr.hpp"
#include "expr/cxx_bind_temporary_expr.hpp"
#include "expr/cxx_bool_literal_expr.hpp"
#include "expr/cxx_const_cast_expr.hpp"
#include "expr/cxx_construct_expr.hpp"
#include "expr/cxx_default_arg_expr.hpp"
#include "expr/cxx_default_init_expr.hpp"
#include "expr/cxx_delete_expr.hpp"
#include "expr/cxx_dependent_scope_member_expr.hpp"
#include "expr/cxx_dynamic_cast_expr.hpp"
#include "expr/cxx_fold_expr.hpp"
#include "expr/cxx_functional_cast_expr.hpp"
#include "expr/cxx_inherited_ctor_init_expr.hpp"
#include "expr/cxx_member_call_expr.hpp"
#include "expr/cxx_new_expr.hpp"
#include "expr/cxx_noexcept_expr.hpp"
#include "expr/cxx_null_ptr_literal_expr.hpp"
#include "expr/cxx_operator_call_expr.hpp"
#include "expr/cxx_paren_list_init_expr.hpp"
#include "expr/cxx_pseudo_destructor_expr.hpp"
#include "expr/cxx_reinterpret_cast_expr.hpp"
#include "expr/cxx_rewritten_binary_operator.hpp"
#include "expr/cxx_scalar_value_init_expr.hpp"
#include "expr/cxx_static_cast_expr.hpp"
#include "expr/cxx_std_initializer_list_expr.hpp"
#include "expr/cxx_temporary_object_expr.hpp"
#include "expr/cxx_this_expr.hpp"
#include "expr/cxx_throw_expr.hpp"
#include "expr/cxx_typeid_expr.hpp"
#include "expr/cxx_unresolved_construct_expr.hpp"
#include "expr/cxx_uuidof_expr.hpp"
#include "expr/decl_ref_expr.hpp"
#include "expr/dependent_coawait_expr.hpp"
#include "expr/dependent_scope_decl_ref_expr.hpp"
#include "expr/designated_init_expr.hpp"
#include "expr/designated_init_update_expr.hpp"
#include "expr/embed_expr.hpp"
#include "expr/expr_with_cleanups.hpp"
#include "expr/expression_trait_expr.hpp"
#include "expr/ext_vector_element_expr.hpp"
#include "expr/fixed_point_literal.hpp"
#include "expr/floating_literal.hpp"
#include "expr/function_parm_pack_expr.hpp"
#include "expr/generic_selection_expr.hpp"
#include "expr/gnu_null_expr.hpp"
#include "expr/imaginary_literal.hpp"
#include "expr/implicit_cast_expr.hpp"
#include "expr/implicit_value_init_expr.hpp"
#include "expr/init_list_expr.hpp"
#include "expr/integer_literal.hpp"
#include "expr/lambda_expr.hpp"
#include "expr/materialize_temporary_expr.hpp"
#include "expr/ms_property_ref_expr.hpp"
#include "expr/ms_property_subscript_expr.hpp"
#include "expr/user_defined_literal.hpp"
#include "type/adjusted_type.hpp"
#include "type/atomic_type.hpp"
#include "type/attributed_type.hpp"
#include "type/auto_type.hpp"
#include "type/bit_int_type.hpp"
#include "type/block_pointer_type.hpp"
#include "type/btf_tag_attributed_type.hpp"
#include "type/builtin_type.hpp"
#include "type/complex_type.hpp"
#include "type/constant_array_type.hpp"
#include "type/constant_matrix_type.hpp"
#include "type/count_attributed_type.hpp"
#include "type/decayed_type.hpp"
#include "type/decltype_type.hpp"
#include "type/deduced_template_specialization_type.hpp"
#include "type/dependent_address_space_type.hpp"
#include "type/dependent_bit_int_type.hpp"
#include "type/dependent_name_type.hpp"
#include "type/dependent_sized_array_type.hpp"
#include "type/dependent_sized_ext_vector_type.hpp"
#include "type/dependent_sized_matrix_type.hpp"
#include "type/dependent_vector_type.hpp"
#include "type/function_proto_type.hpp"
#include "type/incomplete_array_type.hpp"
#include "type/macro_qualified_type.hpp"
#include "type/member_pointer_type.hpp"
#include "type/pack_expansion_type.hpp"
#include "type/pack_indexing_type.hpp"
#include "type/paren_type.hpp"
#include "type/pointer_type.hpp"
#include "type/variable_array_type.hpp"
#if CLANG_VERSION_MAJOR >= 22
#include "type/predefined_sugar_type.hpp"
#endif
#include "type/l_value_reference_type.hpp"
#include "type/r_value_reference_type.hpp"
#if CLANG_VERSION_MAJOR >= 22
#include "type/subst_builtin_template_pack_type.hpp"
#endif
#include "type/dependent_decltype_type.hpp"
#include "type/dependent_type_of_expr_type.hpp"
#include "type/enum_type.hpp"
#include "type/ext_vector_type.hpp"
#include "type/injected_class_name_type.hpp"
#include "type/record_type.hpp"
#include "type/subst_template_type_parm_pack_type.hpp"
#include "type/subst_template_type_parm_type.hpp"
#include "type/template_specialization_type.hpp"
#include "type/template_type_parm_type.hpp"
#include "type/type_of_expr_type.hpp"
#include "type/type_of_type.hpp"
#include "type/typedef_type.hpp"
#include "type/unary_transform_type.hpp"
#include "type/unresolved_using_type.hpp"
#include "type/using_type.hpp"
#include "type/vector_type.hpp"

namespace ctk::clang_layer::serialization {
namespace {
template <class Serializer>
bool select(const clang::DynTypedNode &node,
            ctk::match::v1::MatchBinding &binding,
            SerializationContext &context) {
  static const Serializer serializer;
  return serializer.serialize(node, binding, context);
}
bool dispatch(const clang::DynTypedNode &node,
              ctk::match::v1::MatchBinding &binding,
              SerializationContext &context) {
  if (const auto *qualified = node.get<clang::QualType>()) {
    helpers::write_type(*qualified, *binding.mutable_qualified_type(), context);
    helpers::finish_binding(binding, context);
    return true;
  }
  // These semantic subclasses share a native ASTNodeKind with their bases.
  if (const auto *type = node.get<clang::Type>()) {
    if (type->getTypeClass() == clang::Type::Decltype &&
        type->isDependentType() && type->isCanonicalUnqualified())
      return select<DependentDecltypeTypeSerializer>(node, binding, context);
    if (type->getTypeClass() == clang::Type::TypeOfExpr &&
        type->isDependentType() && type->isCanonicalUnqualified())
      return select<DependentTypeOfExprTypeSerializer>(node, binding, context);
  }
  const auto kind = node.getNodeKind().asStringRef();
#define CTK_AST_NODE(Type, field)                                              \
  if (kind == #Type)                                                           \
    return select<Type##Serializer>(node, binding, context);
#define CTK_AST_NODE_DECL(Type, field) CTK_AST_NODE(Type, field)
#define CTK_AST_NODE_STMT(Type, field) CTK_AST_NODE(Type, field)
#define CTK_AST_NODE_EXPR(Type, field) CTK_AST_NODE(Type, field)
#define CTK_AST_NODE_TYPE(Type, field) CTK_AST_NODE(Type, field)
#include "node_serializer_catalog.inc"
#undef CTK_AST_NODE_TYPE
#undef CTK_AST_NODE_EXPR
#undef CTK_AST_NODE_STMT
#undef CTK_AST_NODE_DECL
#undef CTK_AST_NODE
  auto *unsupported = binding.mutable_unsupported();
  unsupported->set_clang_kind(kind.str());
  unsupported->set_clang_class(kind.str());
  unsupported->set_reason(ctk::ast::v1::UNSUPPORTED_REASON_DEFERRED_CONTRACT);
  unsupported->set_detail(
      "native node has no supported semantic payload in this catalog");
  helpers::unavailable(kind.str(), unsupported->detail(), context);
  helpers::finish_binding(binding, context);
  return false;
}
} // namespace
bool NodeSerializerDispatcher::serialize(const clang::DynTypedNode &node,
                                         ctk::match::v1::MatchBinding &binding,
                                         SerializationContext &context) {
  if (context.depth == 0) {
    context.complete = true;
    context.nodes = 0;
    context.availability.clear();
    context.availability_starts.clear();
  }
  if (context.depth >= context.max_depth ||
      context.nodes >= context.max_nodes) {
    auto &a = context.availability.emplace_back();
    a.set_field_path(node.getNodeKind().asStringRef().str());
    a.set_state(ctk::ast::v1::FIELD_STATE_TRUNCATED);
    a.set_reason("owned semantic child expansion limit reached");
    context.complete = false;
    binding.set_is_complete(false);
    *binding.add_availability() = a;
    return false;
  }
  const bool parent_complete = context.complete;
  context.complete = true;
  context.availability_starts.push_back(context.availability.size());
  ++context.depth;
  ++context.nodes;
  bool result;
  try {
    result = dispatch(node, binding, context);
  } catch (...) {
    --context.depth;
    context.availability_starts.pop_back();
    context.complete = false;
    throw;
  }
  if (result) {
    binding.add_supported_scopes(ctk::match::v1::BINDING_MATCH_SCOPE_ROOT_ONLY);
    if (node.get<clang::Decl>() || node.get<clang::Stmt>())
      binding.add_supported_scopes(ctk::match::v1::BINDING_MATCH_SCOPE_SUBTREE);
  }
  const bool child_complete = context.complete;
  --context.depth;
  context.availability_starts.pop_back();
  context.complete = parent_complete && child_complete;
  return result;
}
} // namespace ctk::clang_layer::serialization
