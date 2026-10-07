#pragma once
#include "../serialization/semantic_helpers.hpp"
#include "analysis/v1/call_graph_node.pb.h"
#include <clang/Analysis/CallGraph.h>
namespace ctk::clang_layer::calls {
void write_node(const clang::CallGraphNode &,
                ctk::analysis::v1::CallGraphNode &,
                serialization::SerializationContext &);
}
