#include "subst_builtin_template_pack_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool SubstBuiltinTemplatePackTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
#if CLANG_VERSION_MAJOR >= 22
  const auto *native = node.get<clang::SubstBuiltinTemplatePackType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_subst_builtin_template_pack_type();
  helpers::write_common(*native, *payload, context);
  helpers::write_template_argument(native->getArgumentPack(), *payload->mutable_argument_pack(), context);
  helpers::finish_binding(binding, context);
  return true;
#else
  (void)node; (void)binding; (void)context;
  return false;
#endif
}

} // namespace ctk::clang_layer::serialization
