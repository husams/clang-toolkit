#include "cfg_value_helpers.hpp"

namespace ctk::clang_layer::control_flow {
void write_initializer(const clang::CXXCtorInitializer &native,
                       ctk::ast::v1::CXXCtorInitializer &value,
                       Context &context) {
  namespace helpers = serialization::helpers;
  if (native.isBaseInitializer())
    helpers::write_type(clang::QualType(native.getBaseClass(), 0),
                        *value.mutable_base_type(), context);
  else if (native.isMemberInitializer())
    helpers::write_symbol(*native.getMember(), *value.mutable_member(),
                          context);
  else if (native.isIndirectMemberInitializer())
    helpers::write_symbol(*native.getIndirectMember(),
                          *value.mutable_indirect_member(), context);
  else if (native.isDelegatingInitializer())
    helpers::write_type(native.getTypeSourceInfo()->getType(),
                        *value.mutable_delegating_type(), context);
  if (native.getInit())
    helpers::write_expr(native.getInit(), *value.mutable_initializer(),
                        context);
  value.set_is_virtual_base(native.isBaseInitializer() &&
                            native.isBaseVirtual());
  value.set_is_pack_expansion(native.isPackExpansion());
}
} // namespace ctk::clang_layer::control_flow
