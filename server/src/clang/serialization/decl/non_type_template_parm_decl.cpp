#include "non_type_template_parm_decl.hpp"
#include "../declaration_helpers.hpp"
#include <clang/AST/ExprConcepts.h>
#include <clang/AST/TypeLoc.h>

namespace ctk::clang_layer::serialization {
bool NonTypeTemplateParmDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::NonTypeTemplateParmDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_non_type_template_parm_decl();
  helpers::write_common(*native, *payload, context);
  payload->set_depth(native->getDepth());
  payload->set_position(native->getPosition());
  payload->set_is_parameter_pack(native->isParameterPack());
  payload->set_default_argument_was_inherited(
      native->defaultArgumentWasInherited());
  if (native->hasDefaultArgument())
    helpers::write_default_argument(
        *native, *payload->mutable_default_argument(), context);
  payload->set_is_pack_expansion(native->isPackExpansion());
  if (native->isExpandedParameterPack())
    for (unsigned index = 0; index < native->getNumExpansionTypes(); ++index) {
      if (!helpers::can_expand(
              *payload, "expanded_parameter_types", context))
        break;
      helpers::write_type(native->getExpansionType(index),
                          *payload->add_expanded_parameter_types(), context);
    }
  if (native->hasPlaceholderTypeConstraint()) {
    auto *constraint = payload->mutable_type_constraint();
    helpers::write_expr(native->getPlaceholderTypeConstraint(),
                        *constraint->mutable_immediately_declared_constraint(),
                        context);
    const auto *automatic = native->getType()->getContainedAutoType();
    auto *reference = constraint->mutable_concept_reference();
#if CLANG_VERSION_MAJOR >= 21
    const clang::ConceptReference *native_reference = nullptr;
    bool reference_from_expression = false;
    if (const auto *source_type = native->getTypeSourceInfo()) {
      const auto automatic_location =
          source_type->getTypeLoc().getContainedAutoTypeLoc();
      if (automatic_location)
        native_reference = automatic_location.getConceptReference();
    }
    // Instantiated declarations can lose their type spelling wrapper while
    // retaining the concept reference in the immediately declared constraint.
    if (!native_reference) {
      const clang::Expr *expression = native->getPlaceholderTypeConstraint();
      if (const auto *fold =
              llvm::dyn_cast_or_null<clang::CXXFoldExpr>(expression))
        expression = fold->getPattern();
      if (const auto *concept_expression =
              llvm::dyn_cast_or_null<clang::ConceptSpecializationExpr>(
                  expression)) {
        native_reference = concept_expression->getConceptReference();
        reference_from_expression = native_reference != nullptr;
      }
    }
    if (native_reference) {
      helpers::write_concept_reference(*native_reference, *reference, context);
      // The immediately declared expression also contains an implicit
      // decltype(parameter) argument; the type-constraint reference omits it.
      if (reference_from_expression && reference->arguments_size() > 0)
        reference->mutable_arguments()->DeleteSubrange(0, 1);
    } else
#endif
    {
      if (automatic->getTypeConstraintConcept()) {
        helpers::write_symbol(*automatic->getTypeConstraintConcept(),
                              *reference->mutable_concept_declaration(),
                              context);
        helpers::write_name(
            automatic->getTypeConstraintConcept()->getDeclName(),
            *reference->mutable_name(), context);
      }
      helpers::unavailable(
          *payload, "type_constraint.concept_reference.found_declaration",
          "this declaration has no stored concept lookup reference", context);
      helpers::unavailable(
          *payload, "type_constraint.concept_reference.qualifier",
          "this declaration has no stored concept qualifier reference",
          context);
      for (const auto &argument : automatic->getTypeConstraintArguments()) {
        if (!helpers::can_expand(*reference, "arguments", context))
          break;
        helpers::write_template_argument(argument, *reference->add_arguments(),
                                         context);
      }
    }
  }
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
