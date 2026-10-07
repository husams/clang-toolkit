#include "cfg_constructor.hpp"
namespace ctk::clang_layer::control_flow {
void CFGConstructorSerializer::serialize(const clang::CFGElement &source,
                                         ctk::analysis::v1::CfgElement &output,
                                         Context &context) const {
  namespace helpers = serialization::helpers;
  const auto native = source.castAs<clang::CFGConstructor>();
  output.set_kind(ctk::analysis::v1::CfgElement::CONSTRUCTOR);
  auto *value = output.mutable_statement();
  helpers::write_stmt(native.getStmt(), *value->mutable_statement(), context);
  if (const auto *construction = native.getConstructionContext())
    write_construction(construction, *value->mutable_construction_context(),
                       context);
}
} // namespace ctk::clang_layer::control_flow
