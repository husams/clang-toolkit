#include "declaration_order.hpp"
namespace ctk::clang_layer::calls {
bool DeclarationOrder::VisitDecl(clang::Decl *declaration) {
  budget_.check();
  ordinals.try_emplace(declaration->getCanonicalDecl(), ordinals.size());
  return true;
}
} // namespace ctk::clang_layer::calls
