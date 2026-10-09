#pragma once

#include "node_serializers.hpp"

namespace ctk::clang_layer::serialization::helpers {

void write_match_metadata(const clang::DynTypedNode &node,
                          ctk::match::v1::MatchBinding &binding,
                          SerializationContext &context);

} // namespace ctk::clang_layer::serialization::helpers
