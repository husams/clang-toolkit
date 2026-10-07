#include "cxx_deduction_guide_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool CXXDeductionGuideDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::CXXDeductionGuideDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_cxx_deduction_guide_decl();
  helpers::write_common(*native, *payload, context);
  helpers::write_symbol(*native->getDeducedTemplate(),
                        *payload->mutable_deduced_template(), context);
  switch (native->getDeductionCandidateKind()) {
  case clang::DeductionCandidate::Normal:
    payload->set_deduction_candidate_kind(
        ctk::ast::v1::DECL_DEDUCTION_CANDIDATE_KIND_NORMAL);
    break;
  case clang::DeductionCandidate::Copy:
    payload->set_deduction_candidate_kind(
        ctk::ast::v1::DECL_DEDUCTION_CANDIDATE_KIND_COPY);
    break;
  case clang::DeductionCandidate::Aggregate:
    payload->set_deduction_candidate_kind(
        ctk::ast::v1::DECL_DEDUCTION_CANDIDATE_KIND_AGGREGATE);
    break;
  }
  if (native->getCorrespondingConstructor())
    helpers::write_symbol(*native->getCorrespondingConstructor(),
                          *payload->mutable_corresponding_constructor(),
                          context);
#if CLANG_VERSION_MAJOR >= 19
  if (native->getSourceDeductionGuide())
    helpers::write_symbol(*native->getSourceDeductionGuide(),
                          *payload->mutable_source_deduction_guide(), context);
  payload->set_source_kind(
      native->getSourceDeductionGuideKind() ==
              clang::CXXDeductionGuideDecl::SourceDeductionGuideKind::Alias
          ? ctk::ast::v1::DECL_SOURCE_DEDUCTION_GUIDE_KIND_ALIAS
          : ctk::ast::v1::DECL_SOURCE_DEDUCTION_GUIDE_KIND_NONE);
#else
  helpers::unavailable(
      *payload, "source_deduction_guide",
      "this Clang version does not expose deduction-guide origin", context);
  helpers::unavailable(
      *payload, "source_kind",
      "this Clang version does not expose deduction-guide origin kind",
      context);
#endif
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
