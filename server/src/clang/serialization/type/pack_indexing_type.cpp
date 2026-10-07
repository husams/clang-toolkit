#include "pack_indexing_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool PackIndexingTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
#if CLANG_VERSION_MAJOR >= 19
  const auto *native = node.get<clang::PackIndexingType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_pack_indexing_type();
  helpers::write_common(*native, *payload, context);
  helpers::write_type(native->getPattern(), *payload->mutable_pattern_type(), context);
  helpers::write_expr(native->getIndexExpr(), *payload->mutable_index_expression(), context);
  if (auto index = native->getSelectedIndex()) payload->set_selected_index(*index);
  if (native->hasSelectedType())
    helpers::write_type(native->getSelectedType(), *payload->mutable_selected_type(), context);
  helpers::finish_binding(binding, context);
  return true;
#else
  (void)node; (void)binding; (void)context;
  return false;
#endif
}

} // namespace ctk::clang_layer::serialization
