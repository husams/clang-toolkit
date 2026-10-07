#include "call_graph_edge.hpp"
namespace ctk::clang_layer::calls {
void write_edge(const clang::CallGraphNode::CallRecord &native,
                ctk::analysis::v1::CallGraphEdge &output,
                serialization::SerializationContext &context) {
  if (native.CallExpr)
    serialization::helpers::write_expr(native.CallExpr, *output.mutable_call(),
                                       context);
  output.set_is_complete(context.complete);
  for (const auto &item : context.availability)
    output.add_availability()->CopyFrom(item);
}
} // namespace ctk::clang_layer::calls
