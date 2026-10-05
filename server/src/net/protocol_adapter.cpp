#include "ctk/net/protocol_adapter.hpp"
#include <filesystem>
#include <stdexcept>

namespace ctk::net {
namespace {
application::FileInput decode_file(const query::v1::FileInput &file) {
  if (file.path().empty() || file.path().find('\0') != std::string::npos)
    throw std::invalid_argument("file.path must be a nonempty pathname");
  if (file.working_directory().empty() ||
      file.working_directory().find('\0') != std::string::npos ||
      !std::filesystem::path(file.working_directory()).is_absolute())
    throw std::invalid_argument(
        "file.working_directory must be an absolute directory");
  for (const auto &argument : file.compile_arguments())
    if (argument.find('\0') != std::string::npos)
      throw std::invalid_argument(
          "compiler arguments cannot contain NUL bytes");
  return {file.path(),
          {file.compile_arguments().begin(), file.compile_arguments().end()},
          file.working_directory()};
}
void copy_violations(const application::Outcome &outcome,
                     query::v1::Rejected &rejected) {
  using application::OutcomeCode;
  switch (outcome.code) {
  case OutcomeCode::ResourceExhausted:
    rejected.set_code("LIMIT_REACHED");
    break;
  case OutcomeCode::InvalidArgument:
    rejected.set_code("INVALID_ARGUMENT");
    break;
  case OutcomeCode::NotFound:
    rejected.set_code("NOT_FOUND");
    break;
  case OutcomeCode::Internal:
    rejected.set_code("INTERNAL");
    break;
  case OutcomeCode::Cancelled:
    rejected.set_code("CANCELLED");
    break;
  case OutcomeCode::FailedPrecondition:
    rejected.set_code("FAILED_PRECONDITION");
    break;
  case OutcomeCode::Ok:
    rejected.set_code("OK");
    break;
  }
  rejected.set_message(outcome.message);
  for (const auto &item : outcome.violations) {
    auto *value = rejected.add_violations();
    value->set_limit_name(item.limit_name);
    value->set_current_value(item.current_value);
    value->set_configured_limit(item.configured_limit);
    value->set_requested_increment(item.requested_increment);
    value->set_projected_value(item.projected_value);
  }
}
} // namespace
application::QueryRequest
RequestDecoder::decode_query(const query::v1::QueryRequest &request) {
  if (request.query().empty())
    throw std::invalid_argument("query must be nonempty");
  application::QueryRequest result{request.query(), {}};
  for (const auto &file : request.files())
    result.files.push_back(decode_file(file));
  return result;
}
application::QueryCommand
RequestDecoder::decode_command(const query::v1::QueryCommand &command) {
  application::QueryCommand result;
  result.request_id = command.request_id();
  switch (command.command_case()) {
  case query::v1::QueryCommand::kStartQuery:
    result.kind = application::CommandKind::StartQuery;
    result.query = command.start_query().query();
    if (result.query.empty())
      throw std::invalid_argument("start_query.query must be nonempty");
    break;
  case query::v1::QueryCommand::kAddFiles:
    result.kind = application::CommandKind::AddFiles;
    for (const auto &file : command.add_files().files())
      result.files.push_back(decode_file(file));
    break;
  case query::v1::QueryCommand::kMatch:
    result.kind = application::CommandKind::Match;
    break;
  case query::v1::QueryCommand::kPause:
    result.kind = application::CommandKind::Pause;
    break;
  case query::v1::QueryCommand::kResume:
    result.kind = application::CommandKind::Resume;
    break;
  default:
    throw std::invalid_argument("exactly one query command is required");
  }
  return result;
}
query::v1::QueryEvent
EventEncoder::encode(const application::QueryEvent &event) {
  query::v1::QueryEvent result;
  result.set_request_id(event.request_id);
  switch (event.kind) {
  case application::EventKind::Queued:
    result.mutable_queued()->set_pending_requests(event.pending_requests);
    break;
  case application::EventKind::Started:
    result.mutable_started();
    break;
  case application::EventKind::Progress: {
    auto *value = result.mutable_progress();
    value->set_file(event.file);
    value->set_profile(event.profile);
    value->set_completed_files(event.completed_files);
    value->set_accepted_files(event.accepted_files);
    break;
  }
  case application::EventKind::Match: {
    auto *value = result.mutable_match();
    value->set_file(event.file);
    value->set_profile(event.profile);
    for (const auto &[name, binding] : event.bindings) {
      auto &target = (*value->mutable_bindings())[name];
      target.set_kind(binding.kind);
      target.set_name(binding.name);
      target.set_type(binding.type);
    }
    break;
  }
  case application::EventKind::Completed: {
    auto *value = result.mutable_completed();
    value->set_completed_files(event.completed_files);
    value->set_match_count(event.match_count);
    break;
  }
  case application::EventKind::Rejected:
    copy_violations(event.outcome, *result.mutable_rejected());
    break;
  case application::EventKind::Control:
    result.mutable_control()->set_action(event.action);
    break;
  }
  return result;
}
grpc::Status GrpcStatusMapper::map(const application::Outcome &outcome) {
  using application::OutcomeCode;
  grpc::StatusCode code = grpc::StatusCode::OK;
  switch (outcome.code) {
  case OutcomeCode::Ok:
    return grpc::Status::OK;
  case OutcomeCode::InvalidArgument:
    code = grpc::StatusCode::INVALID_ARGUMENT;
    break;
  case OutcomeCode::ResourceExhausted:
    code = grpc::StatusCode::RESOURCE_EXHAUSTED;
    break;
  case OutcomeCode::NotFound:
    code = grpc::StatusCode::NOT_FOUND;
    break;
  case OutcomeCode::Internal:
    code = grpc::StatusCode::INTERNAL;
    break;
  case OutcomeCode::Cancelled:
    code = grpc::StatusCode::CANCELLED;
    break;
  case OutcomeCode::FailedPrecondition:
    code = grpc::StatusCode::FAILED_PRECONDITION;
    break;
  }
  query::v1::Rejected details;
  copy_violations(outcome, details);
  return {code, outcome.message, details.SerializeAsString()};
}
} // namespace ctk::net
