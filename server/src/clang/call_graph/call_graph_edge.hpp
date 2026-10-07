#pragma once
#include "../serialization/semantic_helpers.hpp"
#include "analysis/v1/call_graph_edge.pb.h"
#include <clang/Analysis/CallGraph.h>
namespace ctk::clang_layer::calls {
void write_edge(const clang::CallGraphNode::CallRecord &,
                ctk::analysis::v1::CallGraphEdge &,
                serialization::SerializationContext &);
}
