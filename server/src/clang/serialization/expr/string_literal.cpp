#include "string_literal.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool StringLiteralSerializer::serialize(const clang::DynTypedNode &node,
                                        ctk::match::v1::MatchBinding &binding,
                                        SerializationContext &context) const {
  const auto *native = node.get<clang::StringLiteral>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_string_literal();
  helpers::write_common(*native, *payload, context);
  payload->set_value(native->getBytes().str());
  payload->set_code_unit_width(native->getCharByteWidth() * 8);
  payload->set_code_unit_count(native->getLength());
  switch (native->getKind()) {
  case clang::StringLiteralKind::Ordinary:
    payload->set_literal_kind(ctk::ast::v1::STRING_LITERAL_KIND_ORDINARY);
    break;
  case clang::StringLiteralKind::Wide:
    payload->set_literal_kind(ctk::ast::v1::STRING_LITERAL_KIND_WIDE);
    break;
  case clang::StringLiteralKind::UTF8:
    payload->set_literal_kind(ctk::ast::v1::STRING_LITERAL_KIND_UTF8);
    break;
  case clang::StringLiteralKind::UTF16:
    payload->set_literal_kind(ctk::ast::v1::STRING_LITERAL_KIND_UTF16);
    break;
  case clang::StringLiteralKind::UTF32:
    payload->set_literal_kind(ctk::ast::v1::STRING_LITERAL_KIND_UTF32);
    break;
  default:
    helpers::unavailable(
        "literal_kind",
        "Clang unevaluated string kind is absent from the protocol enum",
        context);
    break;
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
