#include "predefined_sugar_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool PredefinedSugarTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
#if CLANG_VERSION_MAJOR >= 22
  const auto *native = node.get<clang::PredefinedSugarType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_predefined_sugar_type();
  helpers::write_common(*native, *payload, context);
  switch (native->getKind()) {
  case clang::PredefinedSugarType::Kind::SizeT: payload->set_predefined_kind(ctk::ast::v1::PREDEFINED_TYPE_KIND_SIZE_T); break;
  case clang::PredefinedSugarType::Kind::SignedSizeT: payload->set_predefined_kind(ctk::ast::v1::PREDEFINED_TYPE_KIND_SIGNED_SIZE_T); break;
  case clang::PredefinedSugarType::Kind::PtrdiffT: payload->set_predefined_kind(ctk::ast::v1::PREDEFINED_TYPE_KIND_PTRDIFF_T); break;
  }
  if (native->getIdentifier()) payload->set_identifier(native->getIdentifier()->getName().str());
  helpers::finish_binding(binding, context);
  return true;
#else
  (void)node; (void)binding; (void)context;
  return false;
#endif
}

} // namespace ctk::clang_layer::serialization
