#pragma once
#include "../serialization/semantic_helpers.hpp"
#include "analysis/v1/cfg_construction_context.pb.h"
#include <clang/Analysis/ConstructionContext.h>

namespace ctk::clang_layer::control_flow {
using Context = serialization::SerializationContext;
inline Context fresh_context(const Context &parent) {
  Context child{parent.ast_context};
  child.projection = parent.projection;
  child.max_depth = parent.max_depth;
  child.max_nodes = parent.max_nodes;
  return child;
}
void write_initializer(const clang::CXXCtorInitializer &,
                       ctk::ast::v1::CXXCtorInitializer &, Context &);
void write_construction(const clang::ConstructionContext *,
                        ctk::analysis::v1::CfgConstructionContext &, Context &);
template <class Value> void finish(Value &value, const Context &context) {
  value.set_is_complete(context.complete);
  for (const auto &entry : context.availability)
    value.add_availability()->CopyFrom(entry);
}
} // namespace ctk::clang_layer::control_flow
