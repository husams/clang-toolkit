#include "cfg_member_dtor.hpp"
namespace ctk::clang_layer::control_flow {
void CFGMemberDtorSerializer::serialize(const clang::CFGElement &source,
                                        ctk::analysis::v1::CfgElement &output,
                                        Context &context) const {
  namespace helpers = serialization::helpers;
  const auto native = source.castAs<clang::CFGMemberDtor>();
  output.set_kind(ctk::analysis::v1::CfgElement::MEMBER_DTOR);
  auto *value = output.mutable_destructor();
  if (const auto *declaration = native.getDestructorDecl(context.ast_context))
    helpers::write_symbol(*declaration, *value->mutable_destructor(), context);
  if (const auto *declaration = native.getDestructorDecl(context.ast_context))
    value->set_is_no_return(declaration->isNoReturn());
  if (const auto *field = native.getFieldDecl())
    helpers::write_symbol(*field, *value->mutable_field(), context);
}
} // namespace ctk::clang_layer::control_flow
