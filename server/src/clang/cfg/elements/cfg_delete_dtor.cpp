#include "cfg_delete_dtor.hpp"
namespace ctk::clang_layer::control_flow {
void CFGDeleteDtorSerializer::serialize(const clang::CFGElement &source,
                                        ctk::analysis::v1::CfgElement &output,
                                        Context &context) const {
  namespace helpers = serialization::helpers;
  const auto native = source.castAs<clang::CFGDeleteDtor>();
  output.set_kind(ctk::analysis::v1::CfgElement::DELETE_DTOR);
  auto *value = output.mutable_destructor();
  if (const auto *declaration = native.getDestructorDecl(context.ast_context))
    helpers::write_symbol(*declaration, *value->mutable_destructor(), context);
  if (const auto *declaration = native.getDestructorDecl(context.ast_context))
    value->set_is_no_return(declaration->isNoReturn());
  if (const auto *record = native.getCXXRecordDecl())
    helpers::write_symbol(*record, *value->mutable_record(), context);
  if (native.getDeleteExpr())
    helpers::write_stmt(native.getDeleteExpr(), *value->mutable_trigger(),
                        context);
}
} // namespace ctk::clang_layer::control_flow
