#pragma once
#include "../node_serializers.hpp"
namespace ctk::clang_layer::serialization {

class CXXStdInitializerListExprSerializer final : public NodeSerializer {
public:
  bool serialize(const clang::DynTypedNode &node,
                 ctk::match::v1::MatchBinding &binding,
                 SerializationContext &context) const override;
};

} // namespace ctk::clang_layer::serialization
