#include "auto_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool AutoTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::AutoType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_auto_type();
  helpers::write_common(*native, *payload, context);
  if (!native->getDeducedType().isNull())
    helpers::write_type(native->getDeducedType(), *payload->mutable_deduced_type(), context);
  switch (native->getKeyword()) {
  case clang::AutoTypeKeyword::Auto: payload->set_keyword(ctk::ast::v1::AUTO_KEYWORD_AUTO); break;
  case clang::AutoTypeKeyword::DecltypeAuto: payload->set_keyword(ctk::ast::v1::AUTO_KEYWORD_DECLTYPE_AUTO); break;
  case clang::AutoTypeKeyword::GNUAutoType: payload->set_keyword(ctk::ast::v1::AUTO_KEYWORD_GNU_AUTO_TYPE); break;
  }
  payload->set_is_constrained(native->isConstrained());
  if (native->getTypeConstraintConcept())
    helpers::write_symbol(*native->getTypeConstraintConcept(), *payload->mutable_type_constraint_concept(), context);
  for (const auto &argument : native->getTypeConstraintArguments()) {
    if (!helpers::can_expand(*payload, "type_constraint_arguments", context)) break;
    helpers::write_template_argument(argument, *payload->add_type_constraint_arguments(), context);
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
