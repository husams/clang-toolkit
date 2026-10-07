#include "character_literal.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool CharacterLiteralSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::CharacterLiteral>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_character_literal();
  helpers::write_common(*native, *payload, context);
  payload->set_value(native->getValue());
  switch (native->getKind()) {
  case clang::CharacterLiteralKind::Ascii:
    payload->set_character_kind(ctk::ast::v1::CHARACTER_KIND_ASCII);
    break;
  case clang::CharacterLiteralKind::Wide:
    payload->set_character_kind(ctk::ast::v1::CHARACTER_KIND_WIDE);
    break;
  case clang::CharacterLiteralKind::UTF8:
    payload->set_character_kind(ctk::ast::v1::CHARACTER_KIND_UTF8);
    break;
  case clang::CharacterLiteralKind::UTF16:
    payload->set_character_kind(ctk::ast::v1::CHARACTER_KIND_UTF16);
    break;
  case clang::CharacterLiteralKind::UTF32:
    payload->set_character_kind(ctk::ast::v1::CHARACTER_KIND_UTF32);
    break;
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
