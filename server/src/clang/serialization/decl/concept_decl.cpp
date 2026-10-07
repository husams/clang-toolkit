#include "concept_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool ConceptDeclSerializer::serialize(const clang::DynTypedNode &node,
                                      ctk::match::v1::MatchBinding &binding,
                                      SerializationContext &context) const {
  const auto *native = node.get<clang::ConceptDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_concept_decl();
  helpers::write_common(*native, *payload, context);
  helpers::write_template_parameters(*native->getTemplateParameters(),
                                     *payload->mutable_template_parameters(),
                                     context);
  if (native->getConstraintExpr())
    helpers::write_expr(native->getConstraintExpr(),
                        *payload->mutable_constraint_expression(), context);
  payload->set_is_type_concept(native->isTypeConcept());
  payload->set_has_definition(native->hasDefinition());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
