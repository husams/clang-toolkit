#include "file_scope_asm_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool FileScopeAsmDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::FileScopeAsmDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_file_scope_asm_decl();
  helpers::write_common(*native, *payload, context);
#if CLANG_VERSION_MAJOR >= 21
  helpers::write_expr(native->getAsmStringExpr(),
                      *payload->mutable_assembly_string(), context);
#else
  helpers::write_expr(native->getAsmString(),
                      *payload->mutable_assembly_string(), context);
#endif
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
