#include "constant_matrix_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool ConstantMatrixTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::ConstantMatrixType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_constant_matrix_type();
  helpers::write_common(*native, *payload, context);
  helpers::write_type(native->getElementType(), *payload->mutable_element_type(), context);
  payload->set_row_count(native->getNumRows());
  payload->set_column_count(native->getNumColumns());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
