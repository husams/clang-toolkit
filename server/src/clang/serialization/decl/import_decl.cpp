#include "import_decl.hpp"
#include "../declaration_helpers.hpp"
#include <clang/Basic/Module.h>

namespace ctk::clang_layer::serialization {
bool ImportDeclSerializer::serialize(const clang::DynTypedNode &node,
                                     ctk::match::v1::MatchBinding &binding,
                                     SerializationContext &context) const {
  const auto *native = node.get<clang::ImportDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_import_decl();
  helpers::write_common(*native, *payload, context);
  if (native->getImportedModule())
    payload->set_imported_module_name(
        native->getImportedModule()->getFullModuleName());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
