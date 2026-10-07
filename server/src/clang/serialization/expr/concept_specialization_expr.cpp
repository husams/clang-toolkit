#include "concept_specialization_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool ConceptSpecializationExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::ConceptSpecializationExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_concept_specialization_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *reference = native->getConceptReference())
    helpers::write_concept_reference(
        *reference, *payload->mutable_concept_reference(), context);
  for (const auto &argument : native->getTemplateArguments()) {
    if (!helpers::can_expand("template_arguments", context))
      break;
    helpers::write_template_argument(
        argument, *payload->add_template_arguments(), context);
  }
  if (!native->isValueDependent())
    payload->set_is_satisfied(native->isSatisfied());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
