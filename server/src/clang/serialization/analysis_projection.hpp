#pragma once
#include "node_serializers.hpp"
#include "analysis/v1/value_projection.pb.h"
#include <stdexcept>

namespace ctk::clang_layer::serialization {
inline void apply_projection(const ctk::analysis::v1::ValueProjection &options,
                             SerializationContext &context) {
  using Projection = ctk::analysis::v1::ValueProjection;
  if (options.mode() != Projection::MODE_UNSPECIFIED &&
      options.mode() != Projection::SHALLOW &&
      options.mode() != Projection::RECURSIVE)
    throw std::invalid_argument("unknown semantic projection mode");
  context.projection = options.mode() == Projection::SHALLOW
                           ? ProjectionPolicy::Shallow
                           : ProjectionPolicy::Recursive;
  if (options.has_max_depth()) {
    if (options.max_depth() < 1 || options.max_depth() > 64)
      throw std::invalid_argument("payload depth must be 1..64");
    context.max_depth = options.max_depth();
  }
  if (options.has_max_nodes()) {
    if (options.max_nodes() < 1 || options.max_nodes() > 100000)
      throw std::invalid_argument("payload nodes must be 1..100000");
    context.max_nodes = options.max_nodes();
  }
}
} // namespace ctk::clang_layer::serialization
