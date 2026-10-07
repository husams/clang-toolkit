#pragma once
#include "../cfg_value_helpers.hpp"
namespace ctk::clang_layer::control_flow {
class ElidedTemporaryObjectConstructionContextSerializer final {
public:
  void serialize(const clang::ElidedTemporaryObjectConstructionContext &,
                 ctk::analysis::v1::CfgConstructionContext &, Context &) const;
};
} // namespace ctk::clang_layer::control_flow
