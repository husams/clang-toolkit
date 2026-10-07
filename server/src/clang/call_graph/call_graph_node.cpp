#include "call_graph_node.hpp"
namespace ctk::clang_layer::calls {
void write_node(const clang::CallGraphNode &native,
                ctk::analysis::v1::CallGraphNode &output,
                serialization::SerializationContext &context) {
  const auto *declaration = native.getDecl();
  output.set_is_virtual_root(!declaration);
  if (declaration) {
    output.set_declaration_kind(declaration->getDeclKindName());
    if (const auto *named = llvm::dyn_cast<clang::NamedDecl>(declaration))
      serialization::helpers::write_symbol(*named, *output.mutable_function(),
                                           context);
    else
      serialization::helpers::write_decl(
          declaration, *output.mutable_anonymous_declaration(), context);
    if (const auto *function = llvm::dyn_cast<clang::FunctionDecl>(declaration))
      output.set_has_definition(function->getDefinition() != nullptr);
    else if (const auto *block = llvm::dyn_cast<clang::BlockDecl>(declaration))
      output.set_has_definition(block->getBody() != nullptr);
  }
  output.set_is_complete(context.complete);
  for (const auto &item : context.availability)
    output.add_availability()->CopyFrom(item);
}
} // namespace ctk::clang_layer::calls
