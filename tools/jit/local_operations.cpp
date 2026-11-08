#include "local_operations.hpp"

#include "analysis.hpp"
#include "ctk/application/match_controller.hpp"
#include "ctk/application/script_controller.hpp"
#include "ctk/clang/tooling.hpp"
#include "documents.hpp"
#include "semantic.hpp"
#include "value_access.hpp"

#include <filesystem>

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

bool emit(Values& runtime, const google::protobuf::Message& value) {
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

template <typename Message> const Value* result(Values& runtime, Message value, bool display) {
  if (display && !emit(runtime, value))
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

api::CompilationProfile profile(llvm::StringRef database) {
  api::CompilationProfile result;
  result.set_working_directory(std::filesystem::current_path().string());
  result.set_compilation_database(database.str());
  return result;
}

} // namespace

LocalOperations::LocalOperations(llvm::StringRef database) : database_(database) {}
LocalOperations::~LocalOperations() = default;

application::MatchController& LocalOperations::controller() {
  if (!controller_) {
    engine_ = clang_layer::make_in_memory_query_engine();
    controller_ = std::make_unique<application::MatchController>(
        application::CursorSettings{}, clang_layer::make_match_backend(engine_));
  }
  return *controller_;
}

bool LocalOperations::is_target(const Value& value) const {
  return message<api::FileInfo>(value) || message<api::InputDescriptor>(value) ||
         message<api::SessionInfo>(value);
}

llvm::Expected<AstHandle> LocalOperations::target(const Value& value) {
  auto& local = controller();
  application::ResourceManager::WorkLease work;
  std::string detail;
  const auto admitted = local.resource_manager()->begin_work(owner, "", work, detail);
  if (admitted != MatchCode::Ok)
    return error(detail);
  api::MatchRequest request;
  request.set_query("translationUnitDecl()");
  api::FileInfo temporary;
  if (const auto* handle = message<api::FileInfo>(value)) {
    request.mutable_file_handle()->set_lease_id(handle->lease_id());
  } else if (const auto* session = message<api::SessionInfo>(value)) {
    request.mutable_session()->set_session_id(session->session_id());
  } else if (const auto* input = message<api::InputDescriptor>(value)) {
    api::OpenFileRequest open;
    *open.mutable_input() = *input;
    if (local.open_file(owner, open, active, temporary, detail) != MatchCode::Ok)
      return error(detail);
    request.mutable_file_handle()->set_lease_id(temporary.lease_id());
  } else {
    return error("expected a retained file or session");
  }
  std::shared_ptr<const clang_layer::NativeBindingState> state;
  const auto reply = local.native_state(owner, request, state, work.token());
  if (!temporary.lease_id().empty()) {
    api::CloseFileRequest close;
    close.set_lease_id(temporary.lease_id());
    api::CloseFileResponse closed;
    local.close_file(owner, close, closed);
  }
  if (reply.code != MatchCode::Ok)
    return error(reply.message);
  auto ast = retain_snapshot(state->snapshot());
  if (!ast)
    return error("retained snapshot has no AST");
  return ast;
}

const Value* LocalOperations::execute(Values& runtime, llvm::StringRef command,
                                      const Sequence& arguments, llvm::StringRef options,
                                      bool display) {
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
    auto& options = *request.mutable_profile();
    options.set_working_directory(std::filesystem::current_path().string());
    options.set_compilation_database(database_);
    if (args.size() > 1) {
      const auto* path = as<std::string>(args[1]);
      if (!path)
        return runtime.fail("script target requires a file path");
      request.mutable_file()->set_file_path(*path);
    }
    if (!script_) {
      application::CursorSettings settings;
      settings.resources = local.resource_manager();
      script_ = std::make_unique<application::ScriptController>(settings, engine_);
    }
    auto reply = script_->run(request, active, owner);
    if (reply.code != MatchCode::Ok)
      return runtime.fail(reply.message);
    return result(runtime, std::move(reply.response), display);
  }
  if (command == "files_expression") {
    api::DiscoverFilesRequest request;
    *request.mutable_profile() = profile(database_);
    const auto* paths = object<Sequence>(first);
    if (text)
      request.add_paths(*text);
    else if (paths) {
      for (const auto& value : paths->items) {
        const auto* path = as<std::string>(value);
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
    return result(runtime, std::move(files), display);
  }
  if (command == "file_open" || command == "file_refresh") {
    api::FileInfo handle;
    MatchCode code;
    std::string detail;
    if (command == "file_open") {
      api::OpenFileRequest request;
      if (text) {
        request.mutable_input()->set_file_path(*text);
        *request.mutable_input()->mutable_profile() = profile(database_);
      } else if (const auto* input = message<api::InputDescriptor>(first)) {
        *request.mutable_input() = *input;
      } else
        return runtime.fail("file open requires a path or discovered input");
      code = local.open_file(owner, request, active, handle, detail);
    } else {
      api::RefreshFileRequest request;
      if (!lease(request, first))
        return runtime.fail("file refresh requires a file handle");
      code = local.refresh_file(owner, request, active, handle, detail);
    }
    if (code != MatchCode::Ok)
      return runtime.fail(detail);
    if (display &&
        !emit_text(runtime, llvm::Twine(command == "file_open" ? "opened " : "refreshed ")
                                .concat(handle.input().file_path())
                                .str()))
      return nullptr;
    return result(runtime, std::move(handle), false);
  }
  if (command == "file_info") {
    api::DescribeFileRequest request;
    api::FileInfo info;
    if (!lease(request, first))
      return runtime.fail("file info requires a file handle");
    if (local.describe_file(owner, request, info) != MatchCode::Ok)
      return runtime.fail("file lease unavailable");
    return result(runtime, std::move(info), display);
  }
  if (command == "file_list") {
    if (!args.empty()) {
      const auto* files = message<api::DiscoverFilesResponse>(first);
      if (!files)
        return runtime.fail("file list discovered in requires a FileSet");
      if (display && !emit(runtime, *files))
        return nullptr;
      return runtime.hold(first);
    }
    auto files = local.list_files(owner);
    if (display && !emit(runtime, files))
      return nullptr;
    std::vector<Value> entries;
    for (const auto& file : files.files())
      entries.push_back({semantic(std::make_unique<api::FileInfo>(file))});
    return runtime.hold(list(std::move(entries), true));
  }
  if (command == "file_close") {
    api::CloseFileResponse closed;
    MatchCode code;
    if (args.empty())
      code = local.close_all_files(owner, closed);
    else {
      api::CloseFileRequest request;
      if (!lease(request, first))
        return runtime.fail("file close requires a file handle");
      code = local.close_file(owner, request, closed);
    }
    if (code != MatchCode::Ok && code != MatchCode::NotFound)
      return runtime.fail("could not release file lease");
    return result(runtime, std::move(closed), display);
  }
  if (command == "resource_status")
    return result(runtime, local.resource_status(), display);
  if (command == "session_list")
    return result(runtime, local.list_sessions(owner), display);
  if (command == "server_status")
    return result(runtime, local.server_status(), display);
  if (command == "cache_status") {
    return result(runtime, local.server_status().cache(), display);
  }
  if (command == "cache_prune") {
    api::PruneCachesRequest request;
    request.set_memory(options == "memory" || options == "all");
    request.set_disk(options == "disk" || options == "all");
    api::PruneCachesResponse response;
    auto reply = local.prune_caches(request, response);
    if (reply.code != MatchCode::Ok)
      return runtime.fail(reply.message);
    return result(runtime, std::move(response), display);
  }

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
    return result(runtime, std::move(info), false);
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
  if (command == "cursor_open") {
    auto& file = *request.mutable_file();
    file.set_file_path(*id);
    file.set_working_directory(std::filesystem::current_path().string());
    file.set_compilation_database(database_);
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
  return result(runtime, std::move(reply.response), display);
}

} // namespace ctk::jit
