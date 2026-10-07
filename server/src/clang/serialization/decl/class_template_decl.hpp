#pragma once
#include "../node_serializers.hpp"

namespace ctk::clang_layer::serialization {
class ClassTemplateDeclSerializer final : public NodeSerializer {
public:
  bool serialize(const clang::DynTypedNode &, ctk::match::v1::MatchBinding &,
                 SerializationContext &) const override;
};
} // namespace ctk::clang_layer::serialization
