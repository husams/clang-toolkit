#include "native_script_environment.hpp"
#include "ctk/script/error.hpp"
#include "file_target_validation.hpp"
#include "pinned_query_engine.hpp"
#include "script_options.hpp"
#include <algorithm>
#include <filesystem>
#include <numeric>
namespace ctk::application::detail {
using Code = ctk::clang_layer::MatchCode;
using ctk::script::Error;
namespace {
void matcher_options(ctk::match::v1::MatchRequest &request,
                     const std::string &operation,
                     const std::map<std::string, ctk::script::Value> &options) {
  for (const auto &[key, value] : options) {
    const auto text = script_text(value);
    if (key == "traversal" && (text == "as_is" || text == "spelled"))
      request.set_traversal_mode(
          text == "spelled"
              ? ctk::match::v1::
                    MATCH_TRAVERSAL_MODE_IGNORE_UNLESS_SPELLED_IN_SOURCE
              : ctk::match::v1::MATCH_TRAVERSAL_MODE_AS_IS);
    else if (key == "scope" && operation == "continue" &&
             (text == "root" || text == "subtree"))
      request.mutable_binding()->set_scope(
          text == "root" ? ctk::match::v1::BINDING_MATCH_SCOPE_ROOT_ONLY
                         : ctk::match::v1::BINDING_MATCH_SCOPE_SUBTREE);
    else
      throw Error(Code::InvalidArgument,
                  "unknown or invalid matcher option: " + key);
  }
}
void validate_binding_scope(
    const ctk::script::Value &rows,
    const ctk::match::v1::BindingMatchTarget &target) {
  if (!rows.wire || !rows.wire->has_matches() || !rows.native_rows ||
      rows.wire->matches().rows_size() !=
          static_cast<int>(rows.native_rows->size()))
    throw Error(Code::InvalidArgument,
                "continuation requires native matched rows");
  const auto scope = target.scope() ==
                             ctk::match::v1::BINDING_MATCH_SCOPE_UNSPECIFIED
                         ? ctk::match::v1::BINDING_MATCH_SCOPE_SUBTREE
                         : target.scope();
  bool selected = false;
  for (int i = 0; i < rows.wire->matches().rows_size(); ++i) {
    if (target.has_match_index() &&
        rows.native_rows->at(static_cast<std::size_t>(i)) !=
            target.match_index())
      continue;
    const auto &bindings = rows.wire->matches().rows(i).bindings();
    const auto found = bindings.find(target.bind());
    if (found == bindings.end())
      continue;
    selected = true;
    const auto &scopes = found->second.supported_scopes();
    if (std::find(scopes.begin(), scopes.end(), scope) == scopes.end())
      throw Error(Code::FailedPrecondition,
                  "binding does not support requested scope");
  }
  if (!selected && !(rows.wire->matches().rows_size() == 0 &&
                     !target.has_match_index()))
    throw Error(Code::NotFound, "binding or row unavailable");
}
} // namespace
NativeScriptEnvironment::NativeScriptEnvironment(
    const ctk::analysis::v1::ScriptRequest &request, CursorSettings settings,
    std::shared_ptr<ctk::clang_layer::IQueryEngine> engine,
    ctk::clang_layer::IMatchBackend::Checkpoint checkpoint)
    : request_(request), settings_(settings),
      checkpoint_(std::move(checkpoint)) {
#ifdef CTK_WITH_CLANG
  pinned_ = std::make_shared<PinnedQueryEngine>(
      engine ? std::move(engine) : ctk::clang_layer::make_query_engine(),
      settings.max_memory_bytes);
  matches_ = ctk::clang_layer::make_match_backend(pinned_);
  traversal_ = ctk::clang_layer::make_traversal_backend(pinned_);
  cfg_ = ctk::clang_layer::make_cfg_backend(pinned_);
  calls_ = ctk::clang_layer::make_call_graph_backend(pinned_);
#endif
}
ctk::match::v1::FileMatchTarget
NativeScriptEnvironment::file_target(const std::string &path) const {
  ctk::match::v1::FileMatchTarget file;
  if (request_.has_file())
    file = request_.file();
  if (request_.has_profile()) {
    file.set_working_directory(request_.profile().working_directory());
    file.set_compilation_database(request_.profile().compilation_database());
    file.clear_compile_arguments();
    *file.mutable_compile_arguments() = request_.profile().compile_arguments();
  }
  file.set_file_path(path);
  if (file.working_directory().empty())
    file.set_working_directory(std::filesystem::current_path().string());
  auto invalid = invalid_file_target(file);
  if (!invalid.empty())
    throw Error(Code::InvalidArgument, invalid);
  return file;
}
void NativeScriptEnvironment::acquire_file(
    const ctk::match::v1::FileMatchTarget &file) {
  if (!matches_)
    throw Error(Code::FailedPrecondition, "Clang analysis is disabled");
  if (!checkpoint_())
    throw Error(Code::Cancelled, "script cancelled");
  // Enforce script snapshot bounds before native backends translate failures.
  pinned_->acquire_snapshot(
      {file.file_path(),
       {file.compile_arguments().begin(), file.compile_arguments().end()},
       file.working_directory(), file.compilation_database()});
  if (!checkpoint_())
    throw Error(Code::Cancelled, "script cancelled");
}
ctk::script::Value
NativeScriptEnvironment::parse_file(const std::string &path) {
  const auto file = file_target(path);
  acquire_file(file);
  ctk::match::v1::ParseRequest request;
  request.set_file_path(file.file_path());
  request.set_working_directory(file.working_directory());
  request.set_compilation_database(file.compilation_database());
  *request.mutable_compile_arguments() = file.compile_arguments();
  auto result = matches_->parse(request, checkpoint_, settings_.results);
  if (result.code != Code::Ok)
    throw Error(result.code, result.message);
  auto wire = std::make_shared<ctk::analysis::v1::ScriptValue>();
  *wire->mutable_tree()->mutable_file() = file;
  return {wire, std::move(result.state), {}};
}
ctk::script::Value
NativeScriptEnvironment::match(const std::string &query,
                               const ctk::script::Value *target,
                               const std::string &binding) {
  return match(query, target, binding, {});
}
ctk::script::Value NativeScriptEnvironment::match(
    const std::string &query, const ctk::script::Value *target,
    const std::string &binding,
    const std::map<std::string, ctk::script::Value> &options) {
  ctk::match::v1::MatchRequest request;
  request.set_query(query);
  request.set_preserve_source(true);
  std::shared_ptr<const ctk::clang_layer::NativeBindingState> previous;
  if (!target) {
    if (!request_.has_file())
      throw Error(Code::InvalidArgument,
                  "match requires a file, parsed tree, or binding target");
    *request.mutable_file() = file_target(request_.file().file_path());
  } else if (!target->wire)
    throw Error(Code::InvalidArgument, "match target has no value");
  else if (target->wire->has_scalar()) {
    if (!binding.empty())
      throw Error(Code::InvalidArgument,
                  "file match target cannot select a binding");
    *request.mutable_file() = file_target(script_text(*target));
  } else if (binding.empty()) {
    if (!target->wire->has_tree() || !target->bindings)
      throw Error(Code::InvalidArgument,
                  "whole-tree match requires a parsed native tree");
    previous = target->bindings;
    request.mutable_session();
  } else {
    if (!target->wire->has_matches() || !target->bindings ||
        !target->native_rows)
      throw Error(Code::InvalidArgument,
                  "binding match requires native matched rows");
    previous = target->bindings;
    auto *selection = request.mutable_binding();
    selection->set_bind(binding);
    if (target->native_rows->size() == 1)
      selection->set_match_index(target->native_rows->front());
  }
  matcher_options(request, "match", options);
  return execute_match(request, std::move(previous));
}
ctk::script::Value NativeScriptEnvironment::execute_match(
    const ctk::match::v1::MatchRequest &request,
    std::shared_ptr<const ctk::clang_layer::NativeBindingState> previous) {
  if (!matches_)
    throw Error(Code::FailedPrecondition, "Clang analysis is disabled");
  if (!checkpoint_())
    throw Error(Code::Cancelled, "script cancelled");
  if (request.has_file())
    acquire_file(request.file());
  auto result = matches_->execute(request, std::move(previous), checkpoint_,
                                  settings_.results);
  if (result.code != Code::Ok)
    throw Error(result.code, result.message);
  auto wire = std::make_shared<ctk::analysis::v1::ScriptValue>();
  for (auto &item : result.rows)
    wire->mutable_matches()->add_rows()->Swap(&item);
  wire->mutable_matches();
  auto indexes = std::make_shared<std::vector<std::size_t>>(result.rows.size());
  std::iota(indexes->begin(), indexes->end(), 0);
  return {wire, std::move(result.state), indexes};
}
ctk::script::Value NativeScriptEnvironment::matching(
    const std::string &name, const std::vector<ctk::script::Value> &arguments,
    const std::map<std::string, ctk::script::Value> &options) {
  ctk::match::v1::MatchRequest request;
  request.set_preserve_source(true);
  std::shared_ptr<const ctk::clang_layer::NativeBindingState> previous;
  const auto arity = name == "match" ? 1U : name == "restart" ? 2U : 3U;
  if (arguments.size() != arity)
    throw Error(Code::InvalidArgument, "wrong argument count for " + name);
  request.set_query(script_text(arguments.back()));
  if (request.query().empty())
    throw Error(Code::InvalidArgument, "matcher expression is required");
  if (name == "match") {
    if (!request_.has_file())
      throw Error(Code::InvalidArgument,
                  "native script operations require a file target");
    *request.mutable_file() = file_target(request_.file().file_path());
  } else {
    const auto &rows = arguments.front();
    if (!rows.wire || !rows.wire->has_matches() || !rows.bindings ||
        !rows.native_rows)
      throw Error(Code::InvalidArgument,
                  "continuation requires native matched rows");
    previous = rows.bindings;
    if (name == "restart")
      request.mutable_session();
    else {
      auto *binding = request.mutable_binding();
      binding->set_bind(script_text(arguments[1]));
      if (binding->bind().empty())
        throw Error(Code::InvalidArgument, "binding name is required");
      if (rows.native_rows->size() == 1)
        binding->set_match_index(rows.native_rows->front());
      matcher_options(request, name, options);
      validate_binding_scope(rows, *binding);
      return execute_match(request, std::move(previous));
    }
  }
  matcher_options(request, name, options);
  return execute_match(request, std::move(previous));
}
ctk::script::Value NativeScriptEnvironment::call(
    const std::string &name, const std::vector<ctk::script::Value> &arguments,
    const std::map<std::string, ctk::script::Value> &options) {
  if (name != "match" && name != "continue" && name != "restart" &&
      name != "traverse" && name != "cfg" && name != "callgraph")
    throw Error(Code::InvalidArgument, "unknown script function: " + name);
  if (!checkpoint_())
    throw Error(Code::Cancelled, "script cancelled");
  if (name == "match" || name == "continue" || name == "restart")
    return matching(name, arguments, options);
  if (!request_.has_file())
    throw Error(Code::InvalidArgument,
                "native script operations require a file target");
  const auto file = file_target(request_.file().file_path());
  acquire_file(file);
  auto wire = std::make_shared<ctk::analysis::v1::ScriptValue>();
  if (name == "cfg") {
    if (arguments.size() != 1)
      throw Error(Code::InvalidArgument, "cfg requires a function name");
    ctk::analysis::v1::CfgRequest request;
    *request.mutable_file() = file;
    request.set_function(script_text(arguments[0]));
    if (request.function().empty())
      throw Error(Code::InvalidArgument, "function name is required");
    for (const auto &[key, value] : options)
      if (key.starts_with("max_"))
        script_option(request, key, value);
      else
        script_option(*request.mutable_options(), key, value);
    auto result =
        cfg_->build(request, checkpoint_,
                    {1000, 100000, 1000000, settings_.results.max_bytes});
    if (result.code != Code::Ok)
      throw Error(result.code, result.message);
    wire->mutable_cfg()->Swap(&result.response);
  } else {
    if (!arguments.empty())
      throw Error(Code::InvalidArgument, name + " takes only named options");
    if (name == "traverse") {
      ctk::analysis::v1::TraverseRequest request;
      *request.mutable_file() = file;
      for (const auto &[key, value] : options)
        script_option(request, key, value);
      auto result = traversal_->traverse(request, checkpoint_,
                                         {100000, settings_.results.max_bytes});
      if (result.code != Code::Ok)
        throw Error(result.code, result.message);
      wire->mutable_traversal()->Swap(&result.response);
    } else {
      ctk::analysis::v1::CallGraphRequest request;
      *request.mutable_file() = file;
      for (const auto &[key, value] : options)
        script_option(request, key, value);
      auto result = calls_->build(
          request, checkpoint_, {100000, 1000000, settings_.results.max_bytes});
      if (result.code != Code::Ok)
        throw Error(result.code, result.message);
      wire->mutable_call_graph()->Swap(&result.response);
    }
  }
  return {wire, {}, {}};
}
} // namespace ctk::application::detail
