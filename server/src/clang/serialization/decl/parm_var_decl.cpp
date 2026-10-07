#include "parm_var_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool ParmVarDeclSerializer::serialize(const clang::DynTypedNode &node,
                                      ctk::match::v1::MatchBinding &binding,
                                      SerializationContext &context) const {
  const auto *native = node.get<clang::ParmVarDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_parm_var_decl();
  helpers::write_common(*native, *payload, context);
  if (native->hasUnparsedDefaultArg())
    helpers::unavailable(*payload, "default_argument",
                         "default argument has not been parsed", context);
  else if (native->hasUninstantiatedDefaultArg())
    helpers::write_expr(native->getUninstantiatedDefaultArg(),
                        *payload->mutable_default_argument(), context);
  else if (native->hasDefaultArg())
    helpers::write_expr(native->getDefaultArg(),
                        *payload->mutable_default_argument(), context);
  payload->set_function_scope_index(native->getFunctionScopeIndex());
  payload->set_function_scope_depth(native->getFunctionScopeDepth());
  payload->set_is_parameter_pack(native->isParameterPack());
#if CLANG_VERSION_MAJOR >= 18
  payload->set_is_explicit_object_parameter(
      native->isExplicitObjectParameter());
#else
  payload->set_is_explicit_object_parameter(false);
#endif
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
