#include "count_attributed_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool CountAttributedTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
#if CLANG_VERSION_MAJOR >= 19
  const auto *native = node.get<clang::CountAttributedType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_count_attributed_type();
  helpers::write_common(*native, *payload, context);
  helpers::write_type(native->desugar(), *payload->mutable_wrapped_type(), context);
  helpers::write_expr(native->getCountExpr(), *payload->mutable_count_expression(), context);
  switch (native->getKind()) {
  case clang::CountAttributedType::CountedBy: payload->set_count_kind(ctk::ast::v1::DYNAMIC_COUNT_KIND_COUNTED_BY); break;
  case clang::CountAttributedType::SizedBy: payload->set_count_kind(ctk::ast::v1::DYNAMIC_COUNT_KIND_SIZED_BY); break;
  case clang::CountAttributedType::CountedByOrNull: payload->set_count_kind(ctk::ast::v1::DYNAMIC_COUNT_KIND_COUNTED_BY_OR_NULL); break;
  case clang::CountAttributedType::SizedByOrNull: payload->set_count_kind(ctk::ast::v1::DYNAMIC_COUNT_KIND_SIZED_BY_OR_NULL); break;
  }
  for (const auto &coupled : native->getCoupledDecls())
    if (coupled.getDecl()) helpers::write_symbol(*coupled.getDecl(), *payload->add_coupled_declarations(), context);
  helpers::finish_binding(binding, context);
  return true;
#else
  (void)node; (void)binding; (void)context;
  return false;
#endif
}

} // namespace ctk::clang_layer::serialization
