#include "pragma_comment_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool PragmaCommentDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::PragmaCommentDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_pragma_comment_decl();
  helpers::write_common(*native, *payload, context);
  switch (native->getCommentKind()) {
  case clang::PCK_Unknown:
    payload->set_comment_kind(ctk::ast::v1::DECL_PRAGMA_COMMENT_KIND_UNKNOWN);
    break;
  case clang::PCK_Linker:
    payload->set_comment_kind(ctk::ast::v1::DECL_PRAGMA_COMMENT_KIND_LINKER);
    break;
  case clang::PCK_Lib:
    payload->set_comment_kind(ctk::ast::v1::DECL_PRAGMA_COMMENT_KIND_LIB);
    break;
  case clang::PCK_Compiler:
    payload->set_comment_kind(ctk::ast::v1::DECL_PRAGMA_COMMENT_KIND_COMPILER);
    break;
  case clang::PCK_ExeStr:
    payload->set_comment_kind(ctk::ast::v1::DECL_PRAGMA_COMMENT_KIND_EXE_STR);
    break;
  case clang::PCK_User:
    payload->set_comment_kind(ctk::ast::v1::DECL_PRAGMA_COMMENT_KIND_USER);
    break;
  }
  payload->set_text(native->getArg().str());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
