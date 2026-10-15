#pragma once
#include "analysis/v1/cfg_request.pb.h"
#include "analysis/v1/cfg_stream.pb.h"
#include "analysis/v1/variable_flow.pb.h"
#include "ctk/clang/cfg_limits.hpp"
#include "ctk/clang/cfg_result.hpp"
namespace ctk::clang_layer {
class ICfgBackend {
public:
  using EventSink = std::function<MatchCode(
      const ctk::analysis::v1::CfgStreamEvent &, std::string &)>;
  using VariableSink = std::function<MatchCode(
      const ctk::analysis::v1::VariableFlowEvent &, std::string &)>;
  virtual CfgResult
  variable_flow(const ctk::analysis::v1::VariableFlowRequest &,
                std::shared_ptr<const NativeBindingState>,
                std::shared_ptr<const NativeBindingState>,
                const IMatchBackend::Checkpoint &, const CfgLimits &,
                const VariableSink &);
  virtual ~ICfgBackend() = default;
  virtual CfgResult
  build_stream(const ctk::analysis::v1::CfgRequest &request,
               std::shared_ptr<const NativeBindingState> previous,
               const IMatchBackend::Checkpoint &checkpoint,
               const CfgLimits &limits, const EventSink &sink);
  virtual CfgResult build(const ctk::analysis::v1::CfgRequest &,
                          const IMatchBackend::Checkpoint &,
                          const CfgLimits &) = 0;
};
std::shared_ptr<ICfgBackend>
make_cfg_backend(std::shared_ptr<IQueryEngine> engine = {});
} // namespace ctk::clang_layer
