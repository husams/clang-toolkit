#include "semantic_helpers.hpp"

namespace ctk::clang_layer::serialization::helpers {
void write_apvalue(const clang::APValue &native, ctk::ast::v1::APValue &value,
                   clang::QualType type, SerializationContext &context) {
  ExpansionFrame frame("APValue.value", context);
  if (!frame.allowed)
    return;
  switch (native.getKind()) {
  case clang::APValue::None:
    value.mutable_no_object();
    break;
  case clang::APValue::Indeterminate:
    value.mutable_indeterminate();
    break;
  case clang::APValue::Int:
    write_apsint(native.getInt(), *value.mutable_integer());
    break;
  case clang::APValue::Float:
    write_apfloat(native.getFloat(), *value.mutable_floating());
    break;
  case clang::APValue::FixedPoint:
    write_apfixed(native.getFixedPoint(), *value.mutable_fixed_point());
    break;
  case clang::APValue::ComplexInt:
    write_apsint(native.getComplexIntReal(),
                 *value.mutable_complex_integer()->mutable_real());
    write_apsint(native.getComplexIntImag(),
                 *value.mutable_complex_integer()->mutable_imaginary());
    break;
  case clang::APValue::ComplexFloat:
    write_apfloat(native.getComplexFloatReal(),
                  *value.mutable_complex_floating()->mutable_real());
    write_apfloat(native.getComplexFloatImag(),
                  *value.mutable_complex_floating()->mutable_imaginary());
    break;
  case clang::APValue::Vector: {
    auto *p = value.mutable_vector();
    clang::QualType element;
    if (!type.isNull())
      if (auto *v = type->getAs<clang::VectorType>())
        element = v->getElementType();
    for (unsigned i = 0; i < native.getVectorLength(); ++i) {
      if (!can_expand(*p, "elements", context))
        break;
      write_apvalue(native.getVectorElt(i), *p->add_elements(), element,
                    context);
    }
    break;
  }
  case clang::APValue::Array: {
    auto *p = value.mutable_array();
    p->set_size(native.getArraySize());
    if (context.projection == ProjectionPolicy::Shallow) {
      (void)can_expand(*p, "initialized_elements", context);
      (void)can_expand(*p, "filler", context);
      break;
    }
    clang::QualType element;
    if (!type.isNull())
      if (auto *a = context.ast_context.getAsArrayType(type))
        element = a->getElementType();
    for (unsigned i = 0; i < native.getArrayInitializedElts(); ++i) {
      if (!can_expand(*p, "initialized_elements", context))
        break;
      write_apvalue(native.getArrayInitializedElt(i),
                    *p->add_initialized_elements(), element, context);
    }
    if (native.hasArrayFiller())
      write_apvalue(native.getArrayFiller(), *p->mutable_filler(), element,
                    context);
    break;
  }
  case clang::APValue::Struct: {
    auto *p = value.mutable_structure();
    if (context.projection == ProjectionPolicy::Shallow) {
      (void)can_expand(*p, "base_values", context);
      (void)can_expand(*p, "field_values", context);
      break;
    }
    const clang::RecordDecl *record =
        type.isNull() ? nullptr : type->getAsRecordDecl();
    const auto *cxx = llvm::dyn_cast_or_null<clang::CXXRecordDecl>(record);
    unsigned i = 0;
    if (cxx)
      for (const auto &base : cxx->bases()) {
        if (i >= native.getStructNumBases())
          break;
        if (!can_expand(*p, "base_values", context))
          break;
        auto *b = p->add_base_values();
        write_type_description(base.getType(), *b->mutable_type(), context);
        write_apvalue(native.getStructBase(i++), *b->mutable_value(),
                      base.getType(), context);
      }
    for (; i < native.getStructNumBases(); ++i) {
      if (!can_expand(*p, "base_values", context))
        break;
      auto *b = p->add_base_values();
      unavailable(*b, "type", "constant record type was not supplied", context);
      write_apvalue(native.getStructBase(i), *b->mutable_value(), {}, context);
    }
    i = 0;
    if (record)
      for (const auto *field : record->fields()) {
        if (field->isUnnamedBitField())
          continue;
        const unsigned index = field->getFieldIndex();
        if (index >= native.getStructNumFields())
          break;
        if (!can_expand(*p, "field_values", context))
          break;
        auto *f = p->add_field_values();
        write_symbol(*field, *f->mutable_field(), context);
        write_apvalue(native.getStructField(index), *f->mutable_value(),
                      field->getType(), context);
        i = index + 1;
      }
    for (; !record && i < native.getStructNumFields(); ++i) {
      if (!can_expand(*p, "field_values", context))
        break;
      auto *f = p->add_field_values();
      unavailable(*f, "field", "constant record type was not supplied",
                  context);
      write_apvalue(native.getStructField(i), *f->mutable_value(), {}, context);
    }
    break;
  }
  case clang::APValue::Union: {
    auto *p = value.mutable_union_value();
    if (context.projection == ProjectionPolicy::Shallow) {
      (void)can_expand(*p, "active_field", context);
      (void)can_expand(*p, "value", context);
      break;
    }
    if (const auto *field = native.getUnionField()) {
      write_symbol(*field, *p->mutable_active_field(), context);
      write_apvalue(native.getUnionValue(), *p->mutable_value(),
                    field->getType(), context);
    }
    break;
  }
  case clang::APValue::LValue: {
    auto *p = value.mutable_lvalue();
    if (context.projection == ProjectionPolicy::Shallow) {
      p->set_offset_bytes(native.getLValueOffset().getQuantity());
      p->set_is_one_past_end(native.isLValueOnePastTheEnd());
      p->set_is_null_pointer(native.isNullPointer());
      (void)can_expand(*p, "base", context);
      (void)can_expand(*p, "path", context);
      break;
    }
    auto base = native.getLValueBase();
    auto *b = p->mutable_base();
    if (base.isNull())
      b->mutable_null_base();
    else if (base.is<const clang::ValueDecl *>())
      write_symbol(*base.get<const clang::ValueDecl *>(),
                   *b->mutable_declaration(), context);
    else if (base.is<const clang::Expr *>())
      write_expr(base.get<const clang::Expr *>(), *b->mutable_expression(),
                 context);
    else if (base.is<clang::TypeInfoLValue>())
      write_type(
          clang::QualType(base.get<clang::TypeInfoLValue>().getType(), 0),
          *b->mutable_type_info()->mutable_type(), context);
    else if (base.is<clang::DynamicAllocLValue>())
      write_type(base.getDynamicAllocType(),
                 *b->mutable_dynamic_allocation()->mutable_type(), context);
    p->set_offset_bytes(native.getLValueOffset().getQuantity());
    p->set_is_one_past_end(native.isLValueOnePastTheEnd());
    p->set_is_null_pointer(native.isNullPointer());
    if (!native.hasLValuePath())
      break;
    auto current = base.isNull() ? clang::QualType{} : base.getType();
    for (const auto &entry : native.getLValuePath()) {
      ExpansionFrame path_frame("APLValue.path", context);
      if (!path_frame.allowed)
        break;
      auto *slot = p->add_path();
      if (!current.isNull() && context.ast_context.getAsArrayType(current)) {
        slot->set_array_index(entry.getAsArrayIndex());
        current = context.ast_context.getAsArrayType(current)->getElementType();
      } else if (!current.isNull() && current->isAnyComplexType()) {
        slot->set_array_index(entry.getAsArrayIndex());
        current = current->getAs<clang::ComplexType>()->getElementType();
      } else if (!current.isNull() && current->isRecordType()) {
        auto subobject = entry.getAsBaseOrMember();
        const auto *decl =
            llvm::dyn_cast_or_null<clang::NamedDecl>(subobject.getPointer());
        if (decl)
          write_symbol(*decl, *slot->mutable_declaration(), context);
        slot->set_is_virtual_base(subobject.getInt());
        if (const auto *field = llvm::dyn_cast_or_null<clang::FieldDecl>(decl))
          current = field->getType();
        else if (const auto *record =
                     llvm::dyn_cast_or_null<clang::RecordDecl>(decl)) {
#if CLANG_VERSION_MAJOR >= 22
          current = context.ast_context.getCanonicalTagType(record);
#else
          current = context.ast_context.getRecordType(record);
#endif
        }
      } else {
        unavailable(*p, "path", "constant lvalue path type is unavailable",
                    context);
        break;
      }
    }
    break;
  }
  case clang::APValue::MemberPointer: {
    auto *p = value.mutable_member_pointer();
    if (context.projection == ProjectionPolicy::Shallow) {
      (void)can_expand(*p, "declaration", context);
      (void)can_expand(*p, "path", context);
      p->set_is_derived_member(native.isMemberPointerToDerivedMember());
      break;
    }
    if (auto *decl = native.getMemberPointerDecl())
      write_symbol(*decl, *p->mutable_declaration(), context);
    for (auto *record : native.getMemberPointerPath()) {
      if (!can_expand(*p, "path", context))
        break;
      write_symbol(*record, *p->add_path(), context);
    }
    p->set_is_derived_member(native.isMemberPointerToDerivedMember());
    break;
  }
  case clang::APValue::AddrLabelDiff:
    auto *p = value.mutable_address_label_difference();
    if (context.projection == ProjectionPolicy::Shallow) {
      (void)can_expand(*p, "left_expression", context);
      (void)can_expand(*p, "right_expression", context);
      break;
    }
    write_expr(
        native.getAddrLabelDiffLHS(),
        *p->mutable_left_expression(), context);
    write_expr(
        native.getAddrLabelDiffRHS(),
        *p->mutable_right_expression(), context);
    break;
  }
}
} // namespace ctk::clang_layer::serialization::helpers
