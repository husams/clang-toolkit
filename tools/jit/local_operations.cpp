#include "local_operations.hpp"
#include "file_values.hpp"
#include "ctk/support/algorithm.hpp"

#include "analysis.hpp"
#include "analysis/v1/call_graph_response.pb.h"
#include "ctk/application/match_controller.hpp"
#include "ctk/application/script_controller.hpp"
#include "ctk/clang/tooling.hpp"
#include "documents.hpp"
#include "embedded_services.hpp"
#include "filters.hpp"
#include "index/v1/index_service.pb.h"
#include "ir.hpp"
#include "semantic.hpp"
#include "value_access.hpp"
#include "workspace.hpp"
#include "platform/repl_cancellation.hpp"

#include <filesystem>
#include <set>
#include <stdexcept>

#include <llvm/ADT/ScopeExit.h>
#include <llvm/Support/JSON.h>

#include <google/protobuf/util/json_util.h>

namespace ctk::jit {
namespace {

namespace api = ctk::match::v1;
using clang_layer::MatchCode;
using namespace value_access;

const std::string owner = "ctk-jit";
bool active() { return true; }

llvm::Error error(const llvm::Twine& message) {
  return llvm::createStringError(llvm::inconvertibleErrorCode(), message);
}

template <typename Message> const Message* message(const Value& value) {
  const auto* proto = semantic_message(value);
  if (!proto || proto->GetDescriptor() != Message::descriptor())
    return nullptr;
  return static_cast<const Message*>(proto);
}

bool emit(Values& runtime, const google::protobuf::Message& value, llvm::StringRef kind) {
  if (runtime.consume_depth)
    return true;
  if (auto text = runtime.present(kind, value))
    return emit_text(runtime, *text);
  google::protobuf::util::JsonPrintOptions options;
  options.add_whitespace = true;
  options.preserve_proto_field_names = true;
  std::string output;
  const auto result = google::protobuf::util::MessageToJsonString(value, &output, options);
  if (!result.ok()) {
    runtime.fail(result.ToString());
    return false;
  }
  return emit_text(runtime, llvm::StringRef(output).rtrim("\n"));
}

template <typename Message>
const Value* result(Values& runtime, Message value, bool display, llvm::StringRef kind) {
  if (display && !emit(runtime, value, kind))
    return nullptr;
  return runtime.hold({semantic(std::make_unique<Message>(std::move(value)))});
}

template <typename Request> bool lease(Request& request, const Value& value) {
  if (const auto* handle = message<api::FileInfo>(value)) {
    request.set_lease_id(handle->lease_id());
    return true;
  }
  if (const auto* id = as<std::string>(value)) {
    request.set_lease_id(*id);
    return true;
  }
  return false;
}

MatchCode close_all_files(application::MatchController& controller,
                          api::CloseFileResponse& response) {
  const auto close = [&](const api::CloseFileRequest& request) {
    api::CloseFileResponse closed;
    const auto code = controller.close_file(owner, request, closed);
    if (code != MatchCode::Ok && code != MatchCode::NotFound)
      return code;
    response.set_released_leases(response.released_leases() + closed.released_leases());
    response.set_closed_cursors(response.closed_cursors() + closed.closed_cursors());
    return MatchCode::Ok;
  };

  // Keep the responses alive while iterating over their protobuf fields in C++17.
  const auto files = controller.list_files(owner);
  api::CloseFileRequest request;
  for (const auto& file : files.files()) {
    if (file.lease_id().empty())
      continue;
    request.set_lease_id(file.lease_id());
    if (const auto code = close(request); code != MatchCode::Ok)
      return code;
  }
  const auto sessions = controller.list_sessions(owner);
  for (const auto& session : sessions.sessions()) {
    request.set_session_id(session.session_id());
    if (const auto code = close(request); code != MatchCode::Ok)
      return code;
  }
  const auto remaining = controller.list_files(owner);
  response.mutable_remaining()->CopyFrom(remaining.files());
  return MatchCode::Ok;
}

api::CompilationProfile profile(const LocalState& settings) {
  api::CompilationProfile result;
  result.set_working_directory(std::filesystem::current_path().string());
  result.set_compilation_database(settings.compilation_database);
  for (const auto& arg : settings.compilation_arguments)
    result.add_compile_arguments(arg);
  return result;
}

} // namespace

struct LocalOperations::BatchScope {
  std::string id;
  const api::OpenResourceScopeRequest& request;
  std::set<const clang::ASTContext*> asts;
  std::set<std::string> completed;
};

LocalOperations::LocalOperations(const LocalState& settings) : settings_(settings) {}
LocalOperations::~LocalOperations() = default;

void LocalOperations::set_events(std::function<void(std::string)> events) {
  events_ = std::move(events);
}

void LocalOperations::finish() {
  if (embedded_)
    embedded_->finish();
}

application::MatchController& LocalOperations::controller() {
  if (!controller_) {
    engine_ = clang_layer::make_query_engine();
    controller_ = std::make_unique<application::MatchController>(
        application::CursorSettings{}, clang_layer::make_match_backend(engine_));
  }
  return *controller_;
}

EmbeddedServices& LocalOperations::embedded() {
  auto& matches = controller();
  if (!embedded_)
    embedded_ = std::make_unique<EmbeddedServices>(engine_, matches, events_);
  return *embedded_;
}

bool LocalOperations::is_target(const Value& value) const {
  return message<api::FileInfo>(value) || message<api::InputDescriptor>(value) ||
         message<api::SessionInfo>(value);
}

llvm::Expected<AstHandle> LocalOperations::target(const Value& value) {
  auto& local = controller();
  std::string detail;
  api::MatchRequest request;
  request.set_query("translationUnitDecl()");
  if (scope_)
    request.set_resource_scope_id(scope_->id);
  api::FileInfo temporary;
  if (const auto* handle = message<api::FileInfo>(value)) {
    request.mutable_file_handle()->set_lease_id(handle->lease_id());
  } else if (const auto* session = message<api::SessionInfo>(value)) {
    request.mutable_session()->set_session_id(session->session_id());
  } else if (const auto* input = message<api::InputDescriptor>(value)) {
    api::OpenFileRequest open;
    *open.mutable_input() = *input;
    if (scope_)
      open.set_resource_scope_id(scope_->id);
    if (local.open_file(owner, open, active, temporary, detail) != MatchCode::Ok)
      return error(detail);
    request.mutable_file_handle()->set_lease_id(temporary.lease_id());
  } else {
    return error("expected a retained file or session");
  }
  auto release = llvm::make_scope_exit([&] {
    if (!scope_ && !temporary.lease_id().empty()) {
      api::CloseFileRequest close;
      close.set_lease_id(temporary.lease_id());
      api::CloseFileResponse closed;
      local.close_file(owner, close, closed);
    }
  });
  application::ResourceManager::WorkLease work;
  const auto admitted =
      local.resource_manager()->begin_work(owner, scope_ ? scope_->id : "", work, detail);
  if (admitted != MatchCode::Ok)
    return error(detail);
  std::shared_ptr<const clang_layer::NativeBindingState> state;
  api::InputDescriptor input;
  application::MatchReply reply;
  try {
    reply = local.native_state(owner, request, state, work.token(), &input);
  } catch (const std::exception& failure) {
    return error(failure.what());
  }
  if (reply.code != MatchCode::Ok)
    return error(reply.message);
  auto ast = retain_snapshot(state->snapshot());
  if (!ast)
    return error("retained snapshot has no AST");
  if (scope_) {
    scope_->asts.insert(ast.get());
    scope_->completed.insert(input.file_path());
  }
  return ast;
}

bool LocalOperations::accepts(const AstHandle& ast) const {
  return !scope_ || ctk::compat::contains(scope_->asts, ast.get());
}

Value LocalOperations::scoped_inputs() const {
  std::vector<Value> items;
  for (const auto& input : scope_->request.inputs())
    items.push_back({semantic(std::make_unique<api::InputDescriptor>(input))});
  return list(std::move(items), true);
}

llvm::Expected<AstHandle> LocalOperations::target_path(llvm::StringRef path) {
  std::error_code issue;
  const auto requested = std::filesystem::weakly_canonical(path.str(), issue);
  if (issue)
    return llvm::errorCodeToError(issue);
  for (const auto& input : scope_->request.inputs()) {
    if (requested == std::filesystem::path(input.file_path())) {
      const Value descriptor{semantic(std::make_unique<api::InputDescriptor>(input))};
      return target(descriptor);
    }
  }
  return error("input is outside the resource scope manifest");
}

llvm::Expected<AstHandle> LocalOperations::parse_snippet(const TargetRequest& target_options,
                                                         llvm::StringRef source,
                                                         const std::vector<std::string>& includes,
                                                         bool translation_unit) {
  api::ParseRequest request;
  request.set_working_directory(target_options.directory.empty()
                                    ? std::filesystem::current_path().string()
                                    : target_options.directory);
  request.set_compilation_database(target_options.compilation_database.empty()
                                       ? settings_.compilation_database
                                       : target_options.compilation_database);
  for (const auto& arg : target_options.arguments)
    request.add_compile_arguments(arg);
  auto* snippet = request.mutable_cpp_snippet();
  snippet->set_code(source.str());
  snippet->set_settings_file(target_options.file);
  snippet->set_translation_unit(translation_unit);
  for (const auto& header : includes)
    snippet->add_includes(header);
  request.set_resource_scope_id(scope_->id);
  auto parsed = controller().parse(owner, request, active);
  if (parsed.code != MatchCode::Ok)
    return error(parsed.message);
  auto lease = std::make_unique<api::FileInfo>();
  lease->set_lease_id(parsed.response.file_lease_id());
  const Value handle{semantic(std::move(lease))};
  return target(handle);
}

namespace {

constexpr std::size_t max_batch_bytes = 1000000;

struct DetachBudget {
  std::size_t items = 0;
  std::size_t bytes = 0;

  void charge(std::size_t size) {
    if (size > max_batch_bytes - bytes || items == max_items)
      throw std::invalid_argument("batch result exceeds the retained value budget");
    ++items;
    bytes += size;
  }
};

Value detach(const Value& value, DetachBudget& budget, unsigned depth = 0) {
  if (depth >= 64)
    throw std::invalid_argument("batch result nesting exceeds 64 levels");
  if (const auto* sequence = object<Sequence>(value)) {
    budget.charge(2);
    std::vector<Value> result;
    for (const auto& item : sequence->items)
      result.push_back(detach(item, budget, depth + 1));
    return list(std::move(result), sequence->tuple);
  }
  if (const auto* record = object<Record>(value)) {
    budget.charge(2);
    auto result = std::make_shared<Record>();
    for (const auto& key : record->keys) {
      budget.charge(key.size());
      result->set(key, detach(record->fields.find(key)->second, budget, depth + 1));
    }
    return {std::move(result)};
  }
  if (as<AstHandle>(value) || object<Runnable>(value) || as<BuiltinFunction>(value) ||
      (semantic_has_live_resource(value) && !message<ctk::analysis::v1::CallGraphResponse>(value)))
    throw std::invalid_argument("batch results cannot retain live resource or callable values");
  if (const auto* node = object<NativeNode>(value)) {
    const auto copy = semantic(*node);
    if (!copy)
      throw std::invalid_argument("could not detach native match binding");
    const Value detached{copy};
    budget.charge(semantic_message(detached)->ByteSizeLong() + 96);
    return detached;
  }
  if (const auto* wire = semantic_message(value)) {
    budget.charge(wire->ByteSizeLong() + 96);
    std::unique_ptr<google::protobuf::Message> copy(wire->New());
    copy->CopyFrom(*wire);
    return {semantic(std::move(copy))};
  }
  const auto* text = as<std::string>(value);
  budget.charge(text ? text->size() : 16);
  return value;
}

} // namespace

const Value* LocalOperations::foreground_batch(Values& runtime, const Sequence& args,
                                               llvm::StringRef options, bool display) {
  if (scope_)
    return runtime.fail("nested batches are not supported");
  const auto* inputs =
      args.items.empty() ? nullptr : message<api::DiscoverFilesResponse>(args.items[0]);
  if (!inputs || args.items.size() != 3 || !object<Runnable>(args.items[2]))
    return runtime.fail("batch input must be a FileSet created with files");
  auto config = llvm::json::parse(options);
  if (!config)
    return runtime.fail(llvm::toString(config.takeError()));
  if (!config->getAsObject())
    return runtime.fail("invalid batch options");
  const auto& fields = *config->getAsObject();
  const auto size = fields.getInteger("size");
  const auto count = fields.getInteger("count");
  if (size.has_value() == count.has_value() || size.value_or(1) < 1 || count.value_or(1) < 1)
    return runtime.fail("batch requires a positive size or count");
  const auto jobs = fields.getInteger("jobs").value_or(4);
  const auto progress = fields.getBoolean("progress").value_or(true);
  const bool continue_on_error = fields.getBoolean("continue_on_error").value_or(false);
  const auto total = static_cast<std::int64_t>(inputs->inputs_size());
  if (count && total && *count > total)
    return runtime.fail("count cannot exceed the nonempty input count");
  auto& local = controller();
  api::OpenResourceScopeRequest request;
  request.set_transient(true);
  request.set_jobs(jobs);
  if (const auto* memory = as<std::string>(args.items[1]))
    request.set_memory_bytes(parse_batch_memory(*memory));

  auto report = std::make_shared<Record>();
  auto number = [&](llvm::StringRef key, std::int64_t value) { report->set(key, {value}); };
  std::vector<Value> results, indices, errors, unconfirmed;
  DetachBudget budget;
  std::int64_t accepted = 0, completed = 0, failed = 0, attempted = 0, skipped = 0;
  std::int64_t completed_files = 0, failed_files = 0, unattempted_files = 0;
  std::uint64_t peak_memory = 0, peak_reserved = 0;
  std::size_t output_chars = 0, peak_output = 0;
  const auto exports_before = runtime.state.successful_exports;
  const auto run_id = new_batch_id().substr(0, 12);
  bool cleanup = true;
  const auto groups = !total ? 0 : size ? (total + *size - 1) / *size : *count;
  auto* workspace = runtime.state.output_path.empty() ? runtime.workspace : nullptr;
  auto show_progress = [&](llvm::StringRef state) {
    if (workspace && progress)
      workspace->progress(llvm::json::Object{
          {"run_id", run_id}, {"total", total}, {"done", completed_files + failed_files},
          {"succeeded", completed_files}, {"failed", failed_files}, {"state", state},
          {"skipped", unattempted_files + (state == "running" ? 0 : total - attempted)}});
  };
  show_progress("running");
  if (display && progress && !workspace &&
      !emit_text(runtime, "batch " + run_id + " started: " + std::to_string(total) +
                              " inputs, jobs " + std::to_string(jobs)))
    return nullptr;
  for (std::int64_t group = 0, offset = 0; group < groups; ++group) {
    if (runtime.cancellable && repl_cancelled()) {
      show_progress("cancelled");
      return runtime.fail("batch cancelled");
    }
    const auto length =
        size ? std::min(*size, total - offset) : total / *count + (group < total % *count);
    request.clear_inputs();
    for (auto i = offset; i < offset + length; ++i)
      *request.add_inputs() = inputs->inputs(i);
    offset += length;
    attempted += length;
    api::ResourceScopeInfo info;
    std::string detail;
    if (local.open_resource_scope(owner, request, info, detail) == MatchCode::Ok) {
      accepted += length;
      scope_ = std::make_unique<BatchScope>(BatchScope{info.resource_scope_id(), request});
      auto cleanup_group = llvm::make_scope_exit([&] {
        api::ResourceScopeInfo released;
        try {
          const auto closed = local.release_resource_scope(owner, scope_->id, released);
          cleanup = closed == MatchCode::Ok && released.cleanup_acknowledged();
          peak_memory = std::max(peak_memory, released.peak_accounted_bytes());
          peak_reserved = std::max(peak_reserved, released.peak_reserved_bytes());
        } catch (...) {
          cleanup = false;
        }
        scope_.reset();
      });
      auto group_value = std::make_shared<Record>();
      group_value->set("index", {group + 1});
      group_value->set("length", {length});
      group_value->set("inputs", scoped_inputs());
      std::vector<Value> paths;
      for (const auto& input : request.inputs())
        paths.push_back({input.file_path()});
      group_value->set("paths", list(std::move(paths), true));
      const Value parameters = list({Value{std::move(group_value)}});
      const Value keywords = record();
      const auto temporary_count = runtime.temporaries.size();
      const auto previous_print = runtime.last_printed;
      const auto previous_result = runtime.result;
      runtime.state.batch_output_bytes = 0;
      if (!display)
        ++runtime.consume_depth;
      auto restore = llvm::make_scope_exit([&] {
        if (!display)
          --runtime.consume_depth;
        const auto used = *runtime.state.batch_output_bytes;
        output_chars += used;
        peak_output = std::max(peak_output, used);
        runtime.state.batch_output_bytes.reset();
        runtime.last_printed = previous_print;
        runtime.result = previous_result;
        runtime.temporaries.resize(temporary_count);
      });
      try {
        const auto* value =
            ctk_jit_value_invoke_v1(&runtime, &args.items[2], &parameters, &keywords);
        if (!value)
          detail = runtime.error;
        else {
          auto candidate = budget;
          candidate.charge(16);
          auto detached = detach(*value, candidate);
          results.push_back(std::move(detached));
          indices.push_back({group + 1});
          budget = candidate;
          ++completed;
        }
      } catch (const std::exception& failure) {
        detail = failure.what();
      }
      const auto processed = std::min(length, static_cast<std::int64_t>(scope_->completed.size()));
      completed_files += processed;
      unattempted_files += length - processed;
      if (!detail.empty()) {
        api::ResourceScopeInfo cancelled;
        local.cancel_resource_scope(owner, scope_->id, cancelled);
      }
    } else {
      failed_files += length;
    }
    if (runtime.fatal || runtime.exit_requested ||
        (runtime.cancellable && repl_cancelled())) {
      const bool cancelled = runtime.cancellable && repl_cancelled();
      show_progress(cancelled || runtime.exit_requested ? "cancelled" : "failed");
      if (cancelled)
        runtime.fail("batch cancelled");
      return nullptr;
    }
    show_progress("running");
    if (!cleanup) {
      unconfirmed.push_back({group + 1});
      if (detail.empty())
        detail = "batch resource cleanup was not acknowledged";
    }
    if (!detail.empty()) {
      ++failed;
      runtime.error.clear();
      if (errors.size() < 4) {
        auto sample = std::make_shared<Record>();
        sample->set("index", {group + 1});
        sample->set("error", {detail.substr(0, 300)});
        errors.push_back({std::move(sample)});
      }
      if (!continue_on_error || !cleanup) {
        skipped = groups - group - 1;
        break;
      }
    }
  }
  report->set("run_id", {run_id});
  number("discovered_inputs", total);
  number("completed_groups", completed);
  number("failed_groups", failed);
  number("skipped_groups", skipped);
  number("accepted_inputs", accepted);
  number("completed_files", completed_files);
  number("failed_files", failed_files);
  number("unattempted_files", unattempted_files);
  number("skipped_files", total - attempted);
  number("cancelled_files", 0);
  number("cancelled_groups", 0);
  number("unknown_files", 0);
  number("group_errors_total", failed);
  number("peak_accounted_bytes", peak_memory);
  number("peak_reserved_bytes", peak_reserved);
  number("exported_outputs", runtime.state.successful_exports - exports_before);
  number("output_chars", output_chars);
  number("cleanup_unknown_groups_total", unconfirmed.size());
  report->set("cleanup_unknown_groups_sample", list(std::move(unconfirmed)));
  if (accepted) {
    const auto resources = local.resource_status();
    std::uint64_t scoped = 0;
    for (const auto& scope : resources.scopes())
      scoped += scope.file_leases();
    number("remaining_external_pins",
           resources.explicit_file_leases() - std::min(scoped, resources.explicit_file_leases()));
  } else
    report->set("remaining_external_pins", {});
  number("peak_group_output_chars", peak_output);
  number("results_count", results.size());
  number("results_bytes", budget.bytes);
  number("result_items", budget.items);
  report->set("status", {std::string(failed ? "failed" : "completed")});
  report->set("cleanup_acknowledged", {cleanup});
  report->set("results_complete", {!failed});
  report->set("group_errors_sample", list(std::move(errors)));
  report->set("results", list(std::move(results)));
  report->set("result_group_indices", list(std::move(indices)));
  show_progress(failed ? "failed" : "completed");
  Value value{std::move(report)};
  if (display && !(workspace && workspace->capture(runtime, "batch_statement", value))) {
    if (auto text = runtime.present("batch_statement", value)) {
      if (!emit_text(runtime, *text))
        return nullptr;
    } else if (progress && !emit_text(runtime, "batch " + std::to_string(completed) + "/" +
                                             std::to_string(groups) + " groups complete")) {
      return nullptr;
    }
  }
  return runtime.hold(std::move(value));
}

api::ServerStatusResponse LocalOperations::status() {
  auto value = controller().server_status();
  index::v1::ListProjectIndexesResponse indexes;
  if (embedded_ && embedded_->index_status(indexes))
    *value.mutable_project_indexes() = std::move(indexes);
  return value;
}

llvm::json::Value LocalOperations::workspace_state(llvm::StringRef kind) {
  if (kind == "status")
    return preview_message(status());
  auto& local = controller();
  return llvm::json::Object{{"files", preview_message(local.list_files(owner))},
                            {"sessions", preview_message(local.list_sessions(owner))}};
}

const Value* LocalOperations::execute(Values& runtime, llvm::StringRef command,
                                      const Sequence& arguments, llvm::StringRef options,
                                      bool display) {
  if (command == "batch_statement") {
    try {
      return foreground_batch(runtime, arguments, options, display);
    } catch (const std::exception& error) {
      return runtime.fail(error.what());
    }
  }
  if (ctk::compat::starts_with(command, "index_") || ctk::compat::starts_with(command, "batch_") ||
      command == "durable_batch" || command == "background" || command == "session_label" ||
      command == "session_start" || command == "session_add" || command == "session_match" ||
      command == "session_pause" || command == "session_resume" || command == "session_close") {
    if (scope_)
      return runtime.fail("operation cannot escape a foreground batch scope");
    return embedded().execute(runtime, command, arguments, options, settings_, display);
  }
  auto& local = controller();
  const auto& args = arguments.items;
  const Value null;
  const auto& first = args.empty() ? null : args.front();
  const auto* text = as<std::string>(first);
  if (command == "script") {
    if (!text)
      return runtime.fail("script requires a source string");
    ctk::analysis::v1::ScriptRequest request;
    request.set_source(*text);
    if (scope_)
      request.set_resource_scope_id(scope_->id);
    auto& options = *request.mutable_profile();
    options.set_working_directory(std::filesystem::current_path().string());
    options.set_compilation_database(settings_.compilation_database);
    for (const auto& arg : settings_.compilation_arguments)
      options.add_compile_arguments(arg);
    if (args.size() > 1) {
      const auto* path = file_path(args[1]);
      if (!path)
        return runtime.fail("script target requires a file path");
      request.mutable_file()->set_file_path(*path);
    }
    auto reply = embedded().scripts().run(request, active, owner);
    if (reply.code != MatchCode::Ok)
      return runtime.fail(reply.message);
    return result(runtime, std::move(reply.response), display, command);
  }
  if (command == "files_expression") {
    text = file_path(first);
    api::DiscoverFilesRequest request;
    *request.mutable_profile() = profile(settings_);
    const auto* paths = object<Sequence>(first);
    if (text)
      request.add_paths(*text);
    else if (paths) {
      for (const auto& value : paths->items) {
        const auto* path = file_path(value);
        if (!path)
          return runtime.fail("files accepts paths, directories, or glob strings");
        request.add_paths(*path);
      }
    } else
      return runtime.fail("files requires a path or list of paths");
    MatchCode code;
    std::string detail;
    auto files = local.discover_files(request, active, code, detail);
    if (code != MatchCode::Ok)
      return runtime.fail(detail);
    return result(runtime, std::move(files), display, command);
  }
  if (command == "file_open" || command == "file_refresh") {
    api::FileInfo handle;
    MatchCode code;
    std::string detail;
    if (command == "file_open") {
      text = file_path(first);
      api::OpenFileRequest request;
      if (text) {
        request.mutable_input()->set_file_path(*text);
        *request.mutable_input()->mutable_profile() = profile(settings_);
      } else if (const auto* input = message<api::InputDescriptor>(first)) {
        *request.mutable_input() = *input;
      } else
        return runtime.fail("file open requires a path or discovered input");
      if (scope_)
        request.set_resource_scope_id(scope_->id);
      code = local.open_file(owner, request, active, handle, detail);
    } else {
      api::RefreshFileRequest request;
      if (!lease(request, first))
        return runtime.fail("file refresh requires a file handle");
      if (scope_)
        request.set_resource_scope_id(scope_->id);
      code = local.refresh_file(owner, request, active, handle, detail);
    }
    if (code != MatchCode::Ok)
      return runtime.fail(detail);
    if (display &&
        !emit_text(runtime, llvm::Twine(command == "file_open" ? "opened " : "refreshed ")
                                .concat(handle.input().file_path())
                                .str()))
      return nullptr;
    return runtime.hold({semantic(std::make_unique<api::FileInfo>(std::move(handle)), true)});
  }
  if (command == "file_info") {
    api::DescribeFileRequest request;
    api::FileInfo info;
    if (!lease(request, first))
      return runtime.fail("file info requires a file handle");
    if (local.describe_file(owner, request, info) != MatchCode::Ok)
      return runtime.fail("file lease unavailable");
    return result(runtime, std::move(info), display, command);
  }
  if (command == "file_list") {
    if (!args.empty()) {
      const auto* files = message<api::DiscoverFilesResponse>(first);
      if (!files)
        return runtime.fail("file list discovered in requires a FileSet");
      if (display && !(runtime.workspace && runtime.workspace->capture(runtime, command, first)) &&
          !emit(runtime, *files, command))
        return nullptr;
      return runtime.hold(first);
    }
    auto files = local.list_files(owner);
    std::vector<Value> entries;
    for (const auto& file : files.files())
      entries.push_back({semantic(std::make_unique<api::FileInfo>(file))});
    auto value = list(std::move(entries), true);
    if (display && !(runtime.workspace && runtime.workspace->capture(runtime, command, value)) &&
        !emit(runtime, files, command))
      return nullptr;
    return runtime.hold(std::move(value));
  }
  if (command == "file_close") {
    api::CloseFileResponse closed;
    MatchCode code;
    if (args.empty())
      code = close_all_files(local, closed);
    else {
      api::CloseFileRequest request;
      if (!lease(request, first))
        return runtime.fail("file close requires a file handle");
      code = local.close_file(owner, request, closed);
    }
    if (code != MatchCode::Ok && code != MatchCode::NotFound)
      return runtime.fail("could not release file lease");
    return result(runtime, std::move(closed), display, command);
  }
  if (command == "resource_status")
    return result(runtime, local.resource_status(), display, command);
  if (command == "session_list") {
    auto sessions = local.list_sessions(owner);
    auto value = Value{semantic(std::make_unique<api::ListSessionsResponse>(sessions))};
    if (display && !(runtime.workspace && runtime.workspace->capture(runtime, command, value)) &&
        !emit(runtime, sessions, command))
      return nullptr;
    return runtime.hold(std::move(value));
  }
  if (command == "server_status")
    return result(runtime, status(), display, command);
  if (command == "cache_status") {
    return result(runtime, local.server_status().cache(), display, command);
  }
  if (command == "cache_prune") {
    api::PruneCachesRequest request;
    request.set_memory(options == "memory" || options == "all");
    request.set_disk(options == "disk" || options == "all");
    api::PruneCachesResponse response;
    auto reply = local.prune_caches(request, response);
    if (reply.code != MatchCode::Ok)
      return runtime.fail(reply.message);
    return result(runtime, std::move(response), display, command);
  }

  if (scope_)
    return runtime.fail("cursor commands cannot escape a foreground batch scope");
  const auto* session = message<api::SessionInfo>(first);
  const auto* previous = message<api::MatchResponse>(first);
  const auto* id = session ? &session->session_id() : previous ? &previous->session_id() : text;
  if (!id)
    return runtime.fail("expected a cursor identifier");
  if (command == "session_attach") {
    api::SessionInfo info;
    auto reply = local.attach_session(owner, *id, info);
    if (reply.code != MatchCode::Ok)
      return runtime.fail(reply.message);
    return result(runtime, std::move(info), false, command);
  }
  if (command == "cursor_close" || command == "session_close_retained") {
    auto reply = local.close(owner, *id);
    if (reply.code != MatchCode::Ok)
      return runtime.fail(reply.message);
    return runtime.hold({});
  }

  const auto* matcher = args.size() > 1 ? as<MatcherValue>(args.back()) : nullptr;
  if (!matcher)
    return runtime.fail("cursor command requires a matcher expression");
  api::BindingMatchTarget selected;
  const auto parsed = google::protobuf::util::JsonStringToMessage(options.str(), &selected);
  if (!parsed.ok())
    return runtime.fail(parsed.ToString());
  api::MatchRequest request;
  request.set_query(matcher->text);
  if (settings_.spelled_only)
    request.set_traversal_mode(api::MATCH_TRAVERSAL_MODE_IGNORE_UNLESS_SPELLED_IN_SOURCE);
  if (command == "cursor_open") {
    auto& file = *request.mutable_file();
    file.set_file_path(*id);
    file.set_working_directory(std::filesystem::current_path().string());
    file.set_compilation_database(settings_.compilation_database);
    for (const auto& arg : settings_.compilation_arguments)
      file.add_compile_arguments(arg);
  } else if (command == "cursor_restart") {
    request.mutable_session()->set_session_id(*id);
    if (selected.has_expected_result_revision())
      request.mutable_session()->set_expected_result_revision(selected.expected_result_revision());
  } else if (command == "cursor_continue") {
    const auto* bind = as<std::string>(args[1]);
    if (!bind)
      return runtime.fail("cursor continue requires a binding name");
    selected.set_session_id(*id);
    selected.set_bind(*bind);
    *request.mutable_binding() = std::move(selected);
  } else
    return runtime.fail("unknown local operation");

  auto reply = local.match(owner, request, active);
  if (reply.code != MatchCode::Ok)
    return runtime.fail(reply.message);
  return result(runtime, std::move(reply.response), display, command);
}

} // namespace ctk::jit
