#include "requires_expr.hpp"
#include "../declaration_helpers.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

namespace {
void write_requirement_info(const clang::concepts::Requirement &native,
                            ctk::ast::v1::RequirementInfo &payload) {
  payload.set_is_dependent(native.isDependent());
  payload.set_contains_unexpanded_parameter_pack(
      native.containsUnexpandedParameterPack());
  if (!native.isDependent())
    payload.set_is_satisfied(native.isSatisfied());
}
void write_diagnostic(
    const clang::concepts::Requirement::SubstitutionDiagnostic &native,
    ctk::ast::v1::SubstitutionDiagnostic &payload) {
  payload.set_message(native.DiagMessage.str());
}
void write_satisfaction(const clang::ASTConstraintSatisfaction &native,
                        ctk::ast::v1::ConstraintSatisfaction &payload,
                        SerializationContext &context) {
  payload.set_is_satisfied(native.IsSatisfied);
  payload.set_contains_errors(native.ContainsErrors);
#if CLANG_VERSION_MAJOR >= 22
  using ConstraintExpressionPointer = const clang::Expr *;
  using ConstraintDiagnosticPointer =
      const clang::ConstraintSubstitutionDiagnostic *;
#else
  using ConstraintExpressionPointer = clang::Expr *;
  using ConstraintDiagnosticPointer =
      std::pair<clang::SourceLocation, llvm::StringRef> *;
#endif
  for (const auto &record : native) {
    if (!helpers::can_expand("details", context))
      break;

    auto *detail = payload.add_details();
    if (auto *expression = record.dyn_cast<ConstraintExpressionPointer>()) {
      helpers::write_expr(expression, *detail->mutable_substituted_constraint(),
                          context);
#if CLANG_VERSION_MAJOR >= 22
    } else if (auto *reference =
                   record.dyn_cast<const clang::ConceptReference *>()) {
      helpers::write_concept_reference(
          *reference, *detail->mutable_concept_reference(), context);
#endif
    } else if (auto *diagnostic =
                   record.dyn_cast<ConstraintDiagnosticPointer>()) {
      detail->mutable_diagnostic()->set_message(diagnostic->second.str());
    }
  }
}
void write_requirement(const clang::concepts::Requirement &native,
                       ctk::ast::v1::ConceptRequirement &payload,
                       SerializationContext &context) {
  using clang::concepts::Requirement;
  switch (native.getKind()) {
  case Requirement::RK_Type: {
    const auto &requirement =
        llvm::cast<clang::concepts::TypeRequirement>(native);
    auto *target = payload.mutable_type();
    write_requirement_info(native, *target->mutable_requirement());
    if (requirement.isSubstitutionFailure())
      write_diagnostic(*requirement.getSubstitutionDiagnostic(),
                       *target->mutable_substitution_error());
    else
      helpers::write_type(requirement.getType()->getType(),
                          *target->mutable_required_type(), context);
    break;
  }
  case Requirement::RK_Simple:
  case Requirement::RK_Compound: {
    const auto &requirement =
        llvm::cast<clang::concepts::ExprRequirement>(native);
    auto *target = payload.mutable_expression();
    write_requirement_info(native, *target->mutable_requirement());
    target->set_is_simple(requirement.isSimple());
    if (requirement.isExprSubstitutionFailure())
      write_diagnostic(*requirement.getExprSubstitutionDiagnostic(),
                       *target->mutable_substitution_error());
    else if (auto *expression = requirement.getExpr())
      helpers::write_expr(expression, *target->mutable_expression(), context);
    const auto &return_requirement = requirement.getReturnTypeRequirement();
    auto *return_target = target->mutable_return_type();
    return_target->set_is_dependent(return_requirement.isDependent());
    return_target->set_contains_unexpanded_parameter_pack(
        return_requirement.containsUnexpandedParameterPack());
    if (return_requirement.isEmpty())
      return_target->mutable_unconstrained();
    else if (return_requirement.isSubstitutionFailure())
      write_diagnostic(*return_requirement.getSubstitutionDiagnostic(),
                       *return_target->mutable_substitution_error());
    else
      helpers::write_template_parameters(
          *return_requirement.getTypeConstraintTemplateParameterList(),
          *return_target->mutable_constraint_parameters(), context);
    using ExprRequirement = clang::concepts::ExprRequirement;
    switch (requirement.getSatisfactionStatus()) {
    case ExprRequirement::SS_Dependent:
      target->set_satisfaction_status(
          ctk::ast::v1::EXPR_REQUIREMENT_SATISFACTION_STATUS_DEPENDENT);
      break;
    case ExprRequirement::SS_ExprSubstitutionFailure:
      target->set_satisfaction_status(
          ctk::ast::v1::
              EXPR_REQUIREMENT_SATISFACTION_STATUS_EXPR_SUBSTITUTION_FAILURE);
      break;
    case ExprRequirement::SS_NoexceptNotMet:
      target->set_satisfaction_status(
          ctk::ast::v1::EXPR_REQUIREMENT_SATISFACTION_STATUS_NOEXCEPT_NOT_MET);
      break;
    case ExprRequirement::SS_TypeRequirementSubstitutionFailure:
      target->set_satisfaction_status(
          ctk::ast::v1::
              EXPR_REQUIREMENT_SATISFACTION_STATUS_TYPE_REQUIREMENT_SUBSTITUTION_FAILURE);
      break;
    case ExprRequirement::SS_ConstraintsNotSatisfied:
      target->set_satisfaction_status(
          ctk::ast::v1::
              EXPR_REQUIREMENT_SATISFACTION_STATUS_CONSTRAINTS_NOT_SATISFIED);
      break;
    case ExprRequirement::SS_Satisfied:
      target->set_satisfaction_status(
          ctk::ast::v1::EXPR_REQUIREMENT_SATISFACTION_STATUS_SATISFIED);
      break;
    }
    if (requirement.getSatisfactionStatus() >=
        ExprRequirement::SS_TypeRequirementSubstitutionFailure) {
      if (auto *constraint =
              requirement.getReturnTypeRequirementSubstitutedConstraintExpr())
        helpers::write_expr(
            constraint, *target->mutable_substituted_return_type_constraint(),
            context);
    }
    break;
  }
  case Requirement::RK_Nested: {
    const auto &requirement =
        llvm::cast<clang::concepts::NestedRequirement>(native);
    auto *target = payload.mutable_nested();
    write_requirement_info(native, *target->mutable_requirement());
    target->set_has_invalid_constraint(requirement.hasInvalidConstraint());
    if (requirement.hasInvalidConstraint())
      target->set_invalid_constraint_entity(
          const_cast<clang::concepts::NestedRequirement &>(requirement)
              .getInvalidConstraintEntity()
              .str());
    else if (auto *constraint = requirement.getConstraintExpr())
      helpers::write_expr(constraint, *target->mutable_constraint_expression(),
                          context);
    if (!requirement.isDependent())
      write_satisfaction(requirement.getConstraintSatisfaction(),
                         *target->mutable_satisfaction(), context);
    break;
  }
  }
}
} // namespace

bool RequiresExprSerializer::serialize(const clang::DynTypedNode &node,
                                       ctk::match::v1::MatchBinding &binding,
                                       SerializationContext &context) const {
  const auto *native = node.get<clang::RequiresExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_requires_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *body = native->getBody())
    helpers::write_decl(body, *payload->mutable_body_declaration(), context);
  if (!native->isValueDependent())
    payload->set_is_satisfied(native->isSatisfied());
  for (const auto *requirement : native->getRequirements()) {
    if (!helpers::can_expand("requirements", context))
      break;
    write_requirement(*requirement, *payload->add_requirements(), context);
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
