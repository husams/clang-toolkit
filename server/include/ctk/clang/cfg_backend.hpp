#pragma once
#include "analysis/v1/cfg_request.pb.h"
#include "ctk/clang/cfg_limits.hpp"
#include "ctk/clang/cfg_result.hpp"
namespace ctk::clang_layer {
class ICfgBackend {
public:
  virtual ~ICfgBackend() = default;
  virtual CfgResult build(const ctk::analysis::v1::CfgRequest &,
                          const IMatchBackend::Checkpoint &,
                          const CfgLimits &) = 0;
};
std::shared_ptr<ICfgBackend>
make_cfg_backend(std::shared_ptr<IQueryEngine> engine = {});
} // namespace ctk::clang_layer
