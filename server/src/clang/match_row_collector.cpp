#include "match_row_collector.hpp"
#include "serialization/match_metadata_helpers.hpp"
#include "serialization/node_serializers.hpp"

namespace ctk::clang_layer {
namespace {
bool same_native_node(const clang::DynTypedNode &left,
                      const clang::DynTypedNode &right) {
  if (!left.getNodeKind().isSame(right.getNodeKind()))
    return false;
  if ((left.getMemoizationData() && right.getMemoizationData()) ||
      left.get<clang::QualType>() || left.get<clang::TypeLoc>() ||
      left.get<clang::NestedNameSpecifierLoc>())
    return left == right;
  if (const auto *argument = left.get<clang::TemplateArgumentLoc>()) {
    const auto *other = right.get<clang::TemplateArgumentLoc>();
    const auto range = argument->getSourceRange();
    return range.isValid() && range == other->getSourceRange() &&
           argument->getArgument().structurallyEquals(other->getArgument());
  }
  // Clang's DynTypedNode equality asserts for other non-memoizable values.
  return false;
}
} // namespace
RowCollector::RowCollector(MatchExecution &result, CapturedBindingState &state,
                           const IMatchBackend::Checkpoint &checkpoint,
                           const MatchLimits &limits,
                           const IMatchBackend::RowSink *sink)
    : result_(result), state_(state), checkpoint_(checkpoint), limits_(limits),
      sink_(sink) {}
void RowCollector::run(const MatchFinder::MatchResult &found) {
  CapturedBindingState::Row nodes;
  for (const auto &[name, node] : found.Nodes.getMap())
    nodes.emplace(name, node);
  emit(nodes, *found.Context);
}
void RowCollector::emit(const CapturedBindingState::Row &nodes,
                        clang::ASTContext &ast) {
  if (result_.code != MatchCode::Ok || !checkpoint_())
    return;
  MatchResult row;
  CapturedBindingState::Row native;
  CapturedBindingState::Row parents;
  if (source_row)
    row.set_source_match_index(*source_row);
  if (target_node) {
    const auto named = nodes.find("target");
    if (named != nodes.end() && !same_native_node(named->second, *target_node)) {
      result_.code = MatchCode::InvalidArgument;
      result_.message =
          "target is reserved for the navigation candidate; "
          "use another name for a nested matcher binding";
      return;
    }
  }
  auto values = nodes;
  if (target_node)
    values.insert_or_assign("target", *target_node);
  for (const auto &[name, node] : values) {
    serialization::SerializationContext context{
        ast, serialization::ProjectionPolicy::Shallow};
    auto &value = (*row.mutable_bindings())[name];
    const bool serialized =
        serialization::NodeSerializerDispatcher::serialize(node, value,
                                                            context);
    if (!serialized && !value.has_unsupported()) {
      result_.code = MatchCode::Internal;
      result_.message = "native binding serialization failed";
      return;
    }
    if (serialized)
      serialization::helpers::write_match_metadata(node, value, context);
    value.add_supported_scopes(ctk::match::v1::BINDING_MATCH_SCOPE_CHILDREN);
    if (target_parent && candidate_node &&
        ((target_node && name == "target") ||
         same_native_node(node, *candidate_node)))
      parents.emplace(name, *target_parent);
    native.emplace(name, node);
  }
  const auto size = row.ByteSizeLong();
  if (!sink_ && size > limits_.max_bytes - bytes_) {
    result_.code = MatchCode::ResourceExhausted;
    result_.message =
        "match response byte limit exceeded (limit " +
        std::to_string(limits_.max_bytes) + " bytes, collected " +
        std::to_string(bytes_) + " bytes, next row " + std::to_string(size) +
        " bytes); increase server.grpc.max_send_message_bytes and "
        "client.grpc.max_receive_message_bytes; no cursor state committed";
    return;
  }
  if (sink_) {
    std::string message;
    const auto code = (*sink_)(row, message);
    if (code != MatchCode::Ok) {
      result_.code = code;
      result_.message = std::move(message);
      return;
    }
    MatchResult metadata;
    if (row.has_source_match_index())
      metadata.set_source_match_index(row.source_match_index());
    for (const auto &[name, full] : row.bindings()) {
      auto &thin = (*metadata.mutable_bindings())[name];
      for (const auto scope : full.supported_scopes())
        thin.add_supported_scopes(
            static_cast<ctk::match::v1::BindingMatchScope>(scope));
    }
    result_.rows.push_back(std::move(metadata));
  } else {
    bytes_ += size;
    result_.rows.push_back(std::move(row));
  }
  state_.append(std::move(native));
  state_.navigation_parents.push_back(std::move(parents));
}
} // namespace ctk::clang_layer
