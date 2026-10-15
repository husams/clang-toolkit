#include "ctk/clang/cfg_backend.hpp"

namespace ctk::clang_layer {
CfgResult
ICfgBackend::build_stream(const ctk::analysis::v1::CfgRequest &request,
                          std::shared_ptr<const NativeBindingState> previous,
                          const IMatchBackend::Checkpoint &checkpoint,
                          const CfgLimits &limits, const EventSink &sink) {
  if (previous)
    return {MatchCode::FailedPrecondition, "retained CFG is unavailable", {}};
  auto result = build(request, checkpoint, limits);
  if (result.code != MatchCode::Ok)
    return result;
  for (const auto &graph : result.response.graphs()) {
    ctk::analysis::v1::CfgStreamEvent event;
    auto *started = event.mutable_graph_started();
    started->set_graph_index(result.graph_count);
    started->mutable_graph()->CopyFrom(graph);
    started->mutable_graph()->clear_blocks();
    int block_fields = 0;
    for (const auto &block : graph.blocks())
      block_fields += block.availability_size();
    auto *fields = started->mutable_graph()->mutable_availability();
    if (block_fields <= fields->size())
      fields->DeleteSubrange(fields->size() - block_fields, block_fields);
    if ((result.code = sink(event, result.message)) != MatchCode::Ok)
      break;
    std::uint64_t elements = 0;
    for (const auto &block : graph.blocks()) {
      event.Clear();
      event.mutable_block()->set_graph_index(result.graph_count);
      event.mutable_block()->mutable_block()->CopyFrom(block);
      if ((result.code = sink(event, result.message)) != MatchCode::Ok)
        break;
      elements += block.elements_size();
    }
    if (result.code != MatchCode::Ok)
      break;
    event.Clear();
    auto *completed = event.mutable_graph_completed();
    completed->set_graph_index(result.graph_count++);
    completed->set_block_count(graph.blocks_size());
    completed->set_element_count(elements);
    completed->set_is_complete(graph.is_complete());
    result.block_count += graph.blocks_size();
    result.element_count += elements;
    if ((result.code = sink(event, result.message)) != MatchCode::Ok)
      break;
  }
  result.response.Clear();
  return result;
}
} // namespace ctk::clang_layer
