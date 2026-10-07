#pragma once
#include "../node_serializers.hpp"
namespace ctk::clang_layer::serialization {
#if CLANG_VERSION_MAJOR >= 22
class MatrixSingleSubscriptExprSerializer final : public NodeSerializer {
public:
  bool serialize(const clang::DynTypedNode &node,
                 ctk::match::v1::MatchBinding &binding,
                 SerializationContext &context) const override;
};
#endif
} // namespace ctk::clang_layer::serialization
