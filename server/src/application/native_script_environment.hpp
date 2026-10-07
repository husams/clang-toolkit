#pragma once
#include "analysis/v1/script_request.pb.h"
#include "ctk/application/match_controller.hpp"
#include "ctk/script/environment.hpp"
namespace ctk::application::detail {
class NativeScriptEnvironment final : public ctk::script::Environment {
public:
  NativeScriptEnvironment(
      const ctk::analysis::v1::ScriptRequest &request, CursorSettings settings,
      std::shared_ptr<ctk::clang_layer::IQueryEngine> engine,
      ctk::clang_layer::IMatchBackend::Checkpoint checkpoint);
  ctk::script::Value
  call(const std::string &, const std::vector<ctk::script::Value> &,
       const std::map<std::string, ctk::script::Value> &) override;
  ctk::script::Value parse_file(const std::string &) override;
  ctk::script::Value match(const std::string &, const ctk::script::Value *,
                           const std::string &) override;
  ctk::script::Value
  match(const std::string &, const ctk::script::Value *, const std::string &,
        const std::map<std::string, ctk::script::Value> &) override;

private:
  ctk::script::Value
  matching(const std::string &, const std::vector<ctk::script::Value> &,
           const std::map<std::string, ctk::script::Value> &);
  ctk::match::v1::FileMatchTarget file_target(const std::string &) const;
  void acquire_file(const ctk::match::v1::FileMatchTarget &);
  ctk::script::Value
  execute_match(const ctk::match::v1::MatchRequest &,
                std::shared_ptr<const ctk::clang_layer::NativeBindingState>);
  ctk::analysis::v1::ScriptRequest request_;
  CursorSettings settings_;
  ctk::clang_layer::IMatchBackend::Checkpoint checkpoint_;
  std::shared_ptr<ctk::clang_layer::IQueryEngine> pinned_;
  std::shared_ptr<ctk::clang_layer::IMatchBackend> matches_;
};
} // namespace ctk::application::detail
