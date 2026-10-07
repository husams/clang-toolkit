#include "match_row_collector.hpp"
#include "serialization/node_serializers.hpp"

namespace ctk::clang_layer {
RowCollector::RowCollector(MatchExecution &result, CapturedBindingState &state,
                           const IMatchBackend::Checkpoint &checkpoint,
                           const MatchLimits &limits)
    : result_(result), state_(state), checkpoint_(checkpoint), limits_(limits) {
}
void RowCollector::run(const MatchFinder::MatchResult &found) {
  if (result_.code != MatchCode::Ok || !checkpoint_())
    return;
  if (result_.rows.size() >= limits_.max_rows) {
    result_.code = MatchCode::ResourceExhausted;
    result_.message = "match row limit exceeded (limit " +
                      std::to_string(limits_.max_rows) +
                      " rows); no cursor state committed";
    return;
  }
  MatchResult row;
  CapturedBindingState::Row native;
  if (source_row)
    row.set_source_match_index(*source_row);
  for (const auto &[name, node] : found.Nodes.getMap()) {
    serialization::SerializationContext context{*found.Context};
    auto &value = (*row.mutable_bindings())[name];
    if (!serialization::NodeSerializerDispatcher::serialize(node, value,
                                                            context) &&
        !value.has_unsupported()) {
      result_.code = MatchCode::Internal;
      result_.message = "native binding serialization failed";
      return;
    }
    native.emplace(name, node);
  }
  const auto size = row.ByteSizeLong();
  if (size > limits_.max_bytes - bytes_) {
    result_.code = MatchCode::ResourceExhausted;
    result_.message =
        "match response byte limit exceeded (limit " +
        std::to_string(limits_.max_bytes) + " bytes, collected " +
        std::to_string(bytes_) + " bytes, next row " + std::to_string(size) +
        " bytes); increase server.grpc.max_send_message_bytes and "
        "client.grpc.max_receive_message_bytes; no cursor state committed";
    return;
  }
  bytes_ += size;
  state_.append(std::move(native));
  result_.rows.push_back(std::move(row));
}
} // namespace ctk::clang_layer
