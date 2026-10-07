#include "ms_guid_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool MSGuidDeclSerializer::serialize(const clang::DynTypedNode &node,
                                     ctk::match::v1::MatchBinding &binding,
                                     SerializationContext &context) const {
  const auto *native = node.get<clang::MSGuidDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_ms_guid_decl();
  helpers::write_common(*native, *payload, context);
  const auto parts = native->getParts();
  payload->set_data1(parts.Part1);
  payload->set_data2(parts.Part2);
  payload->set_data3(parts.Part3);
  payload->set_data4(reinterpret_cast<const char *>(parts.Part4And5),
                     sizeof(parts.Part4And5));
  helpers::write_apvalue(native->getAsAPValue(),
                         *payload->mutable_value_as_constant(),
                         native->getType(), context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
