#pragma once
#include "../cfg_value_helpers.hpp"
namespace ctk::clang_layer::control_flow {
class CXX17ElidedCopyConstructorInitializerConstructionContextSerializer final {
public:
  void serialize(
      const clang::CXX17ElidedCopyConstructorInitializerConstructionContext &,
      ctk::analysis::v1::CfgConstructionContext &, Context &) const;
};
} // namespace ctk::clang_layer::control_flow
