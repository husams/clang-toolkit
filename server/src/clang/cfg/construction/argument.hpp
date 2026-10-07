#pragma once
#include "../cfg_value_helpers.hpp"
namespace ctk::clang_layer::control_flow {
class ArgumentConstructionContextSerializer final {
public:
  void serialize(const clang::ArgumentConstructionContext &,
                 ctk::analysis::v1::CfgConstructionContext &, Context &) const;
};
} // namespace ctk::clang_layer::control_flow
