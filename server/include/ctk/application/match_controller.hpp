#pragma once
#include "ctk/application/operation_executor.hpp"

#include "ctk/clang/matching.hpp"
#include <chrono>
#include <memory>

namespace ctk::application {
struct CursorSettings {
  std::size_t workers{3}, pending_requests{100}, max_cursors{100};
  std::uint64_t max_memory_bytes{2147483648ULL};
  std::chrono::milliseconds idle_ttl{300000};
  ctk::clang_layer::MatchLimits results;
};
struct MatchReply {
  ctk::clang_layer::MatchCode code{ctk::clang_layer::MatchCode::Ok};
  std::string message;
  ctk::match::v1::MatchResponse response;
};
struct ParseReply {
  ctk::clang_layer::MatchCode code{ctk::clang_layer::MatchCode::Ok};
  std::string message;
  ctk::match::v1::ParseResponse response;
};
class MatchController final {
public:
  explicit MatchController(
      CursorSettings settings = {},
      std::shared_ptr<ctk::clang_layer::IMatchBackend> backend = {},
      std::shared_ptr<OperationExecutor> executor = {});
  ~MatchController();
  ParseReply
  parse(const std::string &owner, const ctk::match::v1::ParseRequest &request,
        const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint);
  MatchReply
  match(const std::string &owner, const ctk::match::v1::MatchRequest &request,
        const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint);
  MatchReply close(const std::string &owner, const std::string &id);
  void stop_admission();

private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};
} // namespace ctk::application
