#include "source_loc_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool SourceLocExprSerializer::serialize(const clang::DynTypedNode &node,
                                        ctk::match::v1::MatchBinding &binding,
                                        SerializationContext &context) const {
  const auto *native = node.get<clang::SourceLocExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_source_loc_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *parent = native->getParentContext()) {
    const auto *declaration = clang::Decl::castFromDeclContext(parent);
    if (auto *named = llvm::dyn_cast<clang::NamedDecl>(declaration))
      helpers::write_symbol(*named, *payload->mutable_parent_context(),
                            context);
    else
      payload->mutable_parent_context()->set_clang_class(
          std::string(declaration->getDeclKindName()) + "Decl");
  }
  payload->set_builtin_name(native->getBuiltinStr().str());
  switch (native->getIdentKind()) {
  case clang::SourceLocIdentKind::Line:
    payload->set_kind(ctk::ast::v1::SOURCE_LOC_EXPR_KIND_LINE);
    break;
  case clang::SourceLocIdentKind::Column:
    payload->set_kind(ctk::ast::v1::SOURCE_LOC_EXPR_KIND_COLUMN);
    break;
  case clang::SourceLocIdentKind::File:
  case clang::SourceLocIdentKind::FileName:
    payload->set_kind(ctk::ast::v1::SOURCE_LOC_EXPR_KIND_FILE);
    break;
  case clang::SourceLocIdentKind::Function:
  case clang::SourceLocIdentKind::FuncSig:
    payload->set_kind(ctk::ast::v1::SOURCE_LOC_EXPR_KIND_FUNCTION);
    break;
  case clang::SourceLocIdentKind::SourceLocStruct:
    helpers::unavailable(
        "kind", "Source location struct builtin has no protocol kind", context);
    break;
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
