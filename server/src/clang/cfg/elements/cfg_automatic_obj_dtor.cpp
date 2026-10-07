#include "cfg_automatic_obj_dtor.hpp"
namespace ctk::clang_layer::control_flow {
void CFGAutomaticObjDtorSerializer::serialize(
    const clang::CFGElement &source, ctk::analysis::v1::CfgElement &output,
    Context &context) const {
  namespace helpers = serialization::helpers;
  const auto native = source.castAs<clang::CFGAutomaticObjDtor>();
  output.set_kind(ctk::analysis::v1::CfgElement::AUTOMATIC_OBJECT_DTOR);
  auto *value = output.mutable_destructor();
  if (const auto *declaration = native.getDestructorDecl(context.ast_context))
    helpers::write_symbol(*declaration, *value->mutable_destructor(), context);
  if (const auto *declaration = native.getDestructorDecl(context.ast_context))
    value->set_is_no_return(declaration->isNoReturn());
  if (const auto *variable = native.getVarDecl())
    helpers::write_symbol(*variable, *value->mutable_variable(), context);
  if (native.getTriggerStmt())
    helpers::write_stmt(native.getTriggerStmt(), *value->mutable_trigger(),
                        context);
}
} // namespace ctk::clang_layer::control_flow
