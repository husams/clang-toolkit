#include "builtin_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool BuiltinTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::BuiltinType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_builtin_type();
  helpers::write_common(*native, *payload, context);
  payload->set_kind(type_helpers::builtin_kind(native->getKind()));
  if (payload->kind() == ctk::ast::v1::BUILTIN_KIND_EXTENDED)
    payload->set_extended_kind_name(native->getName(context.ast_context.getPrintingPolicy()).str());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
