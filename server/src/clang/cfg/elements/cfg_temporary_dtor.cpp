#include "cfg_temporary_dtor.hpp"
namespace ctk::clang_layer::control_flow {
void CFGTemporaryDtorSerializer::serialize(
    const clang::CFGElement &source, ctk::analysis::v1::CfgElement &output,
    Context &context) const {
  namespace helpers = serialization::helpers;
  const auto native = source.castAs<clang::CFGTemporaryDtor>();
  output.set_kind(ctk::analysis::v1::CfgElement::TEMPORARY_DTOR);
  auto *value = output.mutable_destructor();
  if (const auto *declaration = native.getDestructorDecl(context.ast_context))
    helpers::write_symbol(*declaration, *value->mutable_destructor(), context);
  if (const auto *declaration = native.getDestructorDecl(context.ast_context))
    value->set_is_no_return(declaration->isNoReturn());
  if (native.getBindTemporaryExpr())
    helpers::write_stmt(native.getBindTemporaryExpr(),
                        *value->mutable_trigger(), context);
}
} // namespace ctk::clang_layer::control_flow
