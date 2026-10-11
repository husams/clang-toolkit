#pragma once
#include "analysis/v1/script_request.pb.h"
#include "ctk/application/match_controller.hpp"
#include "ctk/clang/call_graph_backend.hpp"
#include "ctk/clang/cfg_backend.hpp"
#include "ctk/clang/snapshot_resource_scope.hpp"
#include "ctk/clang/traversal_backend.hpp"
#include "ctk/script/environment.hpp"
#include <set>
namespace ctk::application::detail {
class NativeScriptEnvironment final : public ctk::script::Environment {
public:
  NativeScriptEnvironment(
      const ctk::analysis::v1::ScriptRequest &request, CursorSettings settings,
      std::shared_ptr<ctk::clang_layer::IQueryEngine> engine,
      ctk::clang_layer::IMatchBackend::Checkpoint checkpoint,
      std::string owner = "local-user");
  ctk::script::Value
  call(const std::string &, const std::vector<ctk::script::Value> &,
       const std::map<std::string, ctk::script::Value> &) override;
  ctk::script::Value parse_file(const std::string &) override;
  ctk::script::Value match(const std::string &, const ctk::script::Value *,
                           const std::string &) override;
  ctk::script::Value
  match(const std::string &, const ctk::script::Value *, const std::string &,
        const std::map<std::string, ctk::script::Value> &) override;
  ctk::script::Value files(const std::string &) override;
  ctk::script::Value save(const std::string &, const ctk::script::Value &,
                         const std::string &) override;
  void begin_batch_group(const ctk::script::Value &, std::size_t,
                         std::size_t, std::uint64_t) override;
  void end_batch_group(bool) override;

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
  std::shared_ptr<ctk::clang_layer::IQueryEngine> engine_;
  std::string owner_;
  ctk::clang_layer::IMatchBackend::Checkpoint checkpoint_;
  std::shared_ptr<ctk::clang_layer::IQueryEngine> pinned_;
  std::shared_ptr<ctk::clang_layer::IMatchBackend> matches_;
  std::shared_ptr<ctk::clang_layer::ITraversalBackend> traversal_;
  std::shared_ptr<ctk::clang_layer::ICfgBackend> cfg_;
  std::shared_ptr<ctk::clang_layer::ICallGraphBackend> calls_;
  struct BackendState {
    std::shared_ptr<ctk::clang_layer::IQueryEngine> pinned;
    std::shared_ptr<ctk::clang_layer::IMatchBackend> matches;
    std::shared_ptr<ctk::clang_layer::ITraversalBackend> traversal;
    std::shared_ptr<ctk::clang_layer::ICfgBackend> cfg;
    std::shared_ptr<ctk::clang_layer::ICallGraphBackend> calls;
  };
  std::vector<BackendState> backend_stack_;
  std::vector<std::string> scope_stack_;
  std::vector<std::unique_ptr<ResourceManager::WorkLease>> work_stack_;
  std::vector<std::unique_ptr<ctk::clang_layer::SnapshotResourceScope>>
      snapshot_scope_stack_;
  std::vector<ctk::clang_layer::IMatchBackend::Checkpoint> checkpoint_stack_;
  std::vector<bool> opened_scope_stack_;
  std::vector<std::set<std::string>> active_input_stack_;
  std::vector<std::uint64_t> memory_limit_stack_;
};
} // namespace ctk::application::detail
