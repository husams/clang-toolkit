#include "member_pointer_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool MemberPointerTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::MemberPointerType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_member_pointer_type();
  helpers::write_common(*native, *payload, context);
  helpers::write_type(native->getPointeeType(), *payload->mutable_pointee_type(), context);
#if CLANG_VERSION_MAJOR >= 21
  helpers::write_nested_name(native->getQualifier(), *payload->mutable_class_qualifier(), context);
#else
  helpers::write_type(clang::QualType(native->getClass(), 0), *payload->mutable_class_qualifier()->mutable_type(), context);
#endif
  payload->set_is_member_function_pointer(native->isMemberFunctionPointer());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
