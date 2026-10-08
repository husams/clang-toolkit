#include "function_proto_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool FunctionProtoTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::FunctionProtoType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_function_proto_type();
  helpers::write_common(*native, *payload, context);
  helpers::write_type(native->getReturnType(), *payload->mutable_return_type(), context);
  for (auto parameter : native->param_types()) {
    if (!helpers::can_expand(*payload, "parameter_types", context)) break;
    helpers::write_type(parameter, *payload->add_parameter_types(), context);
  }
  payload->set_is_variadic(native->isVariadic());
  type_helpers::write_function_ext(*native, *payload->mutable_ext_info(), context);
  type_helpers::write_function_proto_ext(*native, *payload->mutable_prototype_info(), context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
