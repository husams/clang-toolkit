#include "semantic_helpers.hpp"
#include <algorithm>
#include <clang/AST/NestedNameSpecifier.h>
#include <llvm/ADT/SmallString.h>
#include <stdexcept>

namespace ctk::clang_layer::serialization::helpers {
namespace {
const char *language_space_name(clang::LangAS space) {
  switch (space) {
  case clang::LangAS::opencl_global:
    return "opencl_global";
  case clang::LangAS::opencl_local:
    return "opencl_local";
  case clang::LangAS::opencl_constant:
    return "opencl_constant";
  case clang::LangAS::opencl_private:
    return "opencl_private";
  case clang::LangAS::opencl_generic:
    return "opencl_generic";
  case clang::LangAS::opencl_global_device:
    return "opencl_global_device";
  case clang::LangAS::opencl_global_host:
    return "opencl_global_host";
  case clang::LangAS::cuda_device:
    return "cuda_device";
  case clang::LangAS::cuda_constant:
    return "cuda_constant";
  case clang::LangAS::cuda_shared:
    return "cuda_shared";
  case clang::LangAS::sycl_global:
    return "sycl_global";
  case clang::LangAS::sycl_global_device:
    return "sycl_global_device";
  case clang::LangAS::sycl_global_host:
    return "sycl_global_host";
  case clang::LangAS::sycl_local:
    return "sycl_local";
  case clang::LangAS::sycl_private:
    return "sycl_private";
  case clang::LangAS::ptr32_sptr:
    return "ptr32_sptr";
  case clang::LangAS::ptr32_uptr:
    return "ptr32_uptr";
  case clang::LangAS::ptr64:
    return "ptr64";
  case clang::LangAS::hlsl_groupshared:
    return "hlsl_groupshared";
#if CLANG_VERSION_MAJOR >= 22
  case clang::LangAS::hlsl_constant:
    return "hlsl_constant";
#endif
#if CLANG_VERSION_MAJOR >= 22
  case clang::LangAS::hlsl_private:
    return "hlsl_private";
#endif
#if CLANG_VERSION_MAJOR >= 22
  case clang::LangAS::hlsl_device:
    return "hlsl_device";
#endif
#if CLANG_VERSION_MAJOR >= 22
  case clang::LangAS::hlsl_input:
    return "hlsl_input";
#endif
#if CLANG_VERSION_MAJOR >= 22
  case clang::LangAS::hlsl_push_constant:
    return "hlsl_push_constant";
#endif
  case clang::LangAS::wasm_funcref:
    return "wasm_funcref";
  default:
    return "unknown_language_address_space";
  }
}
void set_complete(google::protobuf::Message &value, bool complete) {
  const auto *f = value.GetDescriptor()->FindFieldByName("is_complete");
  if (f)
    value.GetReflection()->SetBool(&value, f, complete);
}
void write_child(const clang::DynTypedNode &native,
                 google::protobuf::Message &value,
                 SerializationContext &context) {
  if (context.projection == ProjectionPolicy::Shallow)
    return;
  ctk::match::v1::MatchBinding binding;
  const bool selected =
      NodeSerializerDispatcher::serialize(native, binding, context);
  set_complete(value, binding.is_complete());
  if (!selected || !binding.has_node())
    return;
  const auto &node = binding.node();
  const auto *source_field = node.GetReflection()->GetOneofFieldDescriptor(
      node, node.GetDescriptor()->FindOneofByName("payload"));
  if (!source_field)
    return;
  const auto *target_field =
      value.GetDescriptor()->FindFieldByName(source_field->name());
  if (!target_field ||
      target_field->message_type() != source_field->message_type()) {
    unavailable(std::string(value.GetDescriptor()->name()),
                "native node is outside the typed child family", context);
    set_complete(value, false);
    return;
  }
  value.GetReflection()
      ->MutableMessage(&value, target_field)
      ->CopyFrom(node.GetReflection()->GetMessage(node, source_field));
}
} // namespace
namespace {
void mark_truncated(const std::string &field_path,
                    SerializationContext &context) {
  context.complete = false;
  for (const auto &entry : context.availability)
    if (entry.state() == ctk::ast::v1::FIELD_STATE_TRUNCATED &&
        entry.field_path() == field_path)
      return;
  auto &entry = context.availability.emplace_back();
  entry.set_field_path(field_path);
  entry.set_state(ctk::ast::v1::FIELD_STATE_TRUNCATED);
  entry.set_reason("semantic expansion limit reached");
}
} // namespace
bool can_expand(const std::string &field_path, SerializationContext &context) {
  if (context.projection == ProjectionPolicy::Shallow) {
    for (const auto &entry : context.availability)
      if (entry.state() == ctk::ast::v1::FIELD_STATE_UNREQUESTED &&
          entry.field_path() == field_path)
        return false;
    auto &entry = context.availability.emplace_back();
    entry.set_field_path(field_path);
    entry.set_state(ctk::ast::v1::FIELD_STATE_UNREQUESTED);
    entry.set_reason("owned child expansion is not part of the shallow projection");
    return false;
  }
  if (context.depth < context.max_depth && context.nodes < context.max_nodes)
    return true;
  mark_truncated(field_path, context);
  return false;
}
bool can_expand(const google::protobuf::Message &owner,
                const std::string &field, SerializationContext &context) {
  const auto *descriptor = owner.GetDescriptor();
  if (!descriptor->FindFieldByName(field))
    throw std::logic_error(
        "shallow projection field " +
        std::string(descriptor->name().data(), descriptor->name().size()) +
        "." + field + " does not exist in the protobuf schema");
  const auto name = descriptor->name();
  return can_expand(std::string(name.data(), name.size()) + "." + field,
                    context);
}
ExpansionFrame::ExpansionFrame(const std::string &field_path,
                               SerializationContext &c)
    : context(c), allowed(c.depth < c.max_depth && c.nodes < c.max_nodes) {
  if (!allowed)
    mark_truncated(field_path, c);
  if (allowed) {
    ++context.depth;
    ++context.nodes;
  }
}
ExpansionFrame::~ExpansionFrame() {
  if (allowed)
    --context.depth;
}
void unavailable(const std::string &field, const std::string &reason,
                 SerializationContext &context) {
  auto &entry = context.availability.emplace_back();
  entry.set_field_path(field);
  entry.set_state(ctk::ast::v1::FIELD_STATE_UNAVAILABLE);
  entry.set_reason(reason);
  context.complete = false;
}
void unavailable(google::protobuf::Message &payload, const std::string &field,
                 const std::string &reason, SerializationContext &context) {
  unavailable(std::string(payload.GetDescriptor()->name()) + "." + field,
              reason, context);
}
void finish_binding(ctk::match::v1::MatchBinding &binding,
                    SerializationContext &context) {
  binding.set_is_complete(context.complete);
  const auto start = context.availability_starts.empty()
                         ? 0
                         : context.availability_starts.back();
  for (std::size_t i = start; i < context.availability.size(); ++i)
    *binding.add_availability() = context.availability[i];
}
void write_decl(const clang::Decl *native,
                ctk::ast::v1::DeclarationValue &value,
                SerializationContext &context) {
  if (native)
    write_child(clang::DynTypedNode::create(*native), value, context);
}
void write_expr(const clang::Expr *native, ctk::ast::v1::ExpressionValue &value,
                SerializationContext &context) {
  if (native)
    write_child(clang::DynTypedNode::create(*native), value, context);
}
void write_stmt(const clang::Stmt *native, ctk::ast::v1::StatementValue &value,
                SerializationContext &context) {
  if (!native)
    return;
  if (context.projection == ProjectionPolicy::Shallow)
    return;
  if (const auto *expr = llvm::dyn_cast<clang::Expr>(native)) {
    write_expr(expr, *value.mutable_expression(), context);
    value.set_is_complete(value.expression().is_complete());
  } else
    write_child(clang::DynTypedNode::create(*native), value, context);
}
void write_type_value(clang::QualType native, ctk::ast::v1::TypeValue &value,
                      SerializationContext &context) {
  if (!native.isNull())
    write_child(clang::DynTypedNode::create(*native.getTypePtr()), value,
                context);
}
void write_type(clang::QualType native, ctk::ast::v1::QualType &value,
                SerializationContext &context) {
  if (native.isNull())
    return;
  write_qualifiers(native.getLocalQualifiers(), *value.mutable_qualifiers());
  write_type_description(native, *value.mutable_description(), context);
  write_type_value(native, *value.mutable_type(), context);
}
void write_qualifiers(clang::Qualifiers native,
                      ctk::ast::v1::Qualifiers &value) {
  value.set_is_const(native.hasConst());
  value.set_is_volatile(native.hasVolatile());
  value.set_is_restrict(native.hasRestrict());
  value.set_is_unaligned(native.hasUnaligned());
  const auto space = native.getAddressSpace();
  if (space == clang::LangAS::Default)
    value.mutable_address_space()->mutable_default_space();
  else if (clang::isTargetAddressSpace(space))
    value.mutable_address_space()->set_target_space(
        clang::toTargetAddressSpace(space));
  else {
    // Language address spaces are preserved separately from target numeric
    // spaces.
    const auto *f = value.address_space().GetDescriptor()->FindFieldByName(
        "language_space");
    if (f)
      value.mutable_address_space()->GetReflection()->SetString(
          value.mutable_address_space(), f, language_space_name(space));
  }
}
void write_type_description(clang::QualType native,
                            ctk::ast::v1::TypeDescription &value,
                            SerializationContext &context) {
  if (native.isNull())
    return;
  ExpansionFrame frame("TypeDescription", context);
  if (!frame.allowed)
    return;
  const clang::PrintingPolicy policy(context.ast_context.getLangOpts());
  value.set_spelling(native.getAsString(policy));
  value.set_canonical_spelling(native.getCanonicalType().getAsString(policy));
  write_qualifiers(native.getQualifiers(), *value.mutable_qualifiers());
  value.set_is_dependent(native->isDependentType());
}
#if CLANG_VERSION_MAJOR >= 22
void write_nested_name(clang::NestedNameSpecifier native,
                       ctk::ast::v1::NestedNameSpecifier &value,
                       SerializationContext &context) {
  if (context.projection == ProjectionPolicy::Shallow) {
    return;
  }
  ExpansionFrame frame("NestedNameSpecifier.value", context);
  if (!frame.allowed)
    return;
  if (native == clang::NestedNameSpecifier::getInvalid()) {
    unavailable(value, "value", "native qualifier is invalid", context);
    return;
  }
  switch (native.getKind()) {
  case clang::NestedNameSpecifier::Kind::Null:
    value.mutable_null_specifier();
    break;
  case clang::NestedNameSpecifier::Kind::Global:
    value.mutable_global();
    break;
  case clang::NestedNameSpecifier::Kind::Type:
    write_type(clang::QualType(native.getAsType(), 0), *value.mutable_type(),
               context);
    break;
  case clang::NestedNameSpecifier::Kind::Namespace: {
    auto [decl, prefix] = native.getAsNamespaceAndPrefix();
    auto *slot = value.mutable_namespace_name();
    write_symbol(*decl, *slot->mutable_declaration(), context);
    if (prefix)
      write_nested_name(prefix, *slot->mutable_prefix(), context);
    break;
  }
  case clang::NestedNameSpecifier::Kind::MicrosoftSuper:
    write_symbol(*native.getAsMicrosoftSuper(),
                 *value.mutable_microsoft_super_record(), context);
    break;
  }
}
#else
void write_nested_name(const clang::NestedNameSpecifier *native,
                       ctk::ast::v1::NestedNameSpecifier &value,
                       SerializationContext &context) {
  if (context.projection == ProjectionPolicy::Shallow) {
    return;
  }
  ExpansionFrame frame("NestedNameSpecifier.value", context);
  if (!frame.allowed)
    return;
  if (!native) {
    value.mutable_null_specifier();
    return;
  }
  switch (native->getKind()) {
  case clang::NestedNameSpecifier::Global:
    value.mutable_global();
    break;
  case clang::NestedNameSpecifier::Namespace:
  case clang::NestedNameSpecifier::NamespaceAlias: {
    auto *decl =
        native->getKind() == clang::NestedNameSpecifier::Namespace
            ? static_cast<const clang::NamedDecl *>(native->getAsNamespace())
            : static_cast<const clang::NamedDecl *>(
                  native->getAsNamespaceAlias());
    auto *slot = value.mutable_namespace_name();
    write_symbol(*decl, *slot->mutable_declaration(), context);
    if (native->getPrefix())
      write_nested_name(native->getPrefix(), *slot->mutable_prefix(), context);
    break;
  }
  case clang::NestedNameSpecifier::TypeSpec:
#if CLANG_VERSION_MAJOR < 21
  case clang::NestedNameSpecifier::TypeSpecWithTemplate:
#endif
    write_type(clang::QualType(native->getAsType(), 0), *value.mutable_type(),
               context);
    break;
  case clang::NestedNameSpecifier::Super:
    write_symbol(*native->getAsRecordDecl(),
                 *value.mutable_microsoft_super_record(), context);
    break;
  case clang::NestedNameSpecifier::Identifier:
    unavailable(
        value, "value",
        "this schema cannot represent an unresolved identifier qualifier",
        context);
    break;
  }
}
#endif
void write_apint(const llvm::APInt &native, ctk::ast::v1::APIntBits &value) {
  value.set_bit_width(native.getBitWidth());
  std::string bytes;
  for (unsigned bit = 0; bit < native.getBitWidth(); bit += 8)
    bytes.push_back(static_cast<char>(native.extractBitsAsZExtValue(
        std::min(8U, native.getBitWidth() - bit), bit)));
  value.set_little_endian_bits(bytes);
  llvm::SmallString<64> decimal;
  native.toString(decimal, 10, false);
  value.set_unsigned_decimal(decimal.str().str());
}
void write_apsint(const llvm::APSInt &native, ctk::ast::v1::APSIntBits &value) {
  write_apint(native, *value.mutable_value());
  value.set_is_unsigned(native.isUnsigned());
  llvm::SmallString<64> decimal;
  native.toString(decimal, 10);
  value.set_decimal_value(decimal.str().str());
}
void write_apfloat(const llvm::APFloat &native,
                   ctk::ast::v1::APFloatBits &value) {
  using A = llvm::APFloat;
  using namespace ctk::ast::v1;
  FloatingSemantics semantics = FLOATING_SEMANTICS_UNSPECIFIED;
  switch (A::SemanticsToEnum(native.getSemantics())) {
  case A::S_IEEEhalf:
    semantics = FLOATING_SEMANTICS_IEEE_HALF;
    break;
  case A::S_BFloat:
    semantics = FLOATING_SEMANTICS_BFLOAT;
    break;
  case A::S_IEEEsingle:
    semantics = FLOATING_SEMANTICS_IEEE_SINGLE;
    break;
  case A::S_IEEEdouble:
    semantics = FLOATING_SEMANTICS_IEEE_DOUBLE;
    break;
  case A::S_IEEEquad:
    semantics = FLOATING_SEMANTICS_IEEE_QUAD;
    break;
  case A::S_x87DoubleExtended:
    semantics = FLOATING_SEMANTICS_X87_DOUBLE_EXTENDED;
    break;
  case A::S_PPCDoubleDouble:
    semantics = FLOATING_SEMANTICS_PPC_DOUBLE_DOUBLE;
    break;
  case A::S_PPCDoubleDoubleLegacy:
    semantics = FLOATING_SEMANTICS_PPC_DOUBLE_DOUBLE_LEGACY;
    break;
  case A::S_Float8E5M2:
    semantics = FLOATING_SEMANTICS_FLOAT8_E5_M2;
    break;
  case A::S_Float8E5M2FNUZ:
    semantics = FLOATING_SEMANTICS_FLOAT8_E5_M2_FNUZ;
    break;
  case A::S_Float8E4M3:
    semantics = FLOATING_SEMANTICS_FLOAT8_E4_M3;
    break;
  case A::S_Float8E4M3FN:
    semantics = FLOATING_SEMANTICS_FLOAT8_E4_M3_FN;
    break;
  case A::S_Float8E4M3FNUZ:
    semantics = FLOATING_SEMANTICS_FLOAT8_E4_M3_FNUZ;
    break;
  case A::S_Float8E4M3B11FNUZ:
    semantics = FLOATING_SEMANTICS_FLOAT8_E4_M3_B11_FNUZ;
    break;
  case A::S_Float8E3M4:
    semantics = FLOATING_SEMANTICS_FLOAT8_E3_M4;
    break;
#if CLANG_VERSION_MAJOR >= 22
  case A::S_FloatTF32:
    semantics = FLOATING_SEMANTICS_FLOAT_TF32;
    break;
  case A::S_Float8E8M0FNU:
    semantics = FLOATING_SEMANTICS_FLOAT8_E8_M0_FNU;
    break;
  case A::S_Float6E3M2FN:
    semantics = FLOATING_SEMANTICS_FLOAT6_E3_M2_FN;
    break;
  case A::S_Float6E2M3FN:
    semantics = FLOATING_SEMANTICS_FLOAT6_E2_M3_FN;
    break;
  case A::S_Float4E2M1FN:
    semantics = FLOATING_SEMANTICS_FLOAT4_E2_M1_FN;
    break;
#endif
  default:
    break;
  }
  value.set_semantics(semantics);
  write_apint(native.bitcastToAPInt(), *value.mutable_bit_pattern());
  llvm::SmallString<64> decimal;
  native.toString(decimal);
  value.set_decimal_value(decimal.str().str());
}
void write_apfixed(const llvm::APFixedPoint &native,
                   ctk::ast::v1::APFixedPointBits &value) {
  write_apint(native.getValue(), *value.mutable_bit_pattern());
  value.set_scale(native.getScale());
  value.set_is_unsigned(!native.isSigned());
  value.set_is_saturated(native.isSaturated());
  value.set_has_unsigned_padding(native.hasPadding());
}
} // namespace ctk::clang_layer::serialization::helpers
