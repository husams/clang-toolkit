#include "ctk/application/match_controller.hpp"
#include "ctk/clang/file_discovery.hpp"
#include "resource_scope_guard.hpp"
#include "cursor_registry.hpp"
#include "file_target_validation.hpp"
#include "query_executor.hpp"
#include "ctk/platform/process_memory.hpp"
#include <algorithm>
#include <atomic>
#include <future>
#include <limits>
#include <map>
#include <mutex>
#include <filesystem>
#include <set>
#include <openssl/rand.h>
#include <openssl/sha.h>

namespace ctk::application {
using ctk::clang_layer::MatchCode;
using namespace ctk::match::v1;
namespace {
MatchReply failure(MatchCode code, std::string message) {
  return {code, std::move(message), {}};
}
std::string invalid_request(const ParseRequest &request) {
  FileMatchTarget file;
  file.set_file_path(request.file_path());
  file.set_working_directory(request.working_directory());
  file.set_compilation_database(request.compilation_database());
  file.mutable_compile_arguments()->CopyFrom(request.compile_arguments());
  return detail::invalid_file_target(file);
}
std::string invalid_request(const MatchRequest &request) {
  if (request.query().empty())
    return "query must not be empty";
  if (!MatchTraversalMode_IsValid(request.traversal_mode()))
    return "invalid traversal mode";
  if (request.target_case() == MatchRequest::TARGET_NOT_SET)
    return "one target is required";
  if (request.has_file()) {
    return detail::invalid_file_target(request.file());
  } else if (request.has_file_handle()) {
    if (!detail::CursorRegistry::valid_id(request.file_handle().lease_id()))
      return "file lease id must be a canonical UUIDv4";
  } else {
    const auto &id = request.has_session() ? request.session().session_id()
                                           : request.binding().session_id();
    if (!detail::CursorRegistry::valid_id(id))
      return "session_id must be a canonical UUIDv4";
    if (request.has_session() &&
        request.session().has_expected_result_revision() &&
        request.session().expected_result_revision() == 0)
      return "revision must be positive";
    if (request.has_binding()) {
      const auto &binding = request.binding();
      if (binding.bind().empty())
        return "bind must not be empty";
      if (!BindingMatchScope_IsValid(binding.scope()))
        return "invalid binding scope";
      if (binding.has_expected_result_revision() &&
          binding.expected_result_revision() == 0)
        return "revision must be positive";
    }
  }
  return {};
}

ctk::match::v1::InputDescriptor input_descriptor(
    const ctk::match::v1::FileMatchTarget &file) {
  ctk::match::v1::InputDescriptor input;
  input.set_file_path(file.file_path());
  auto *profile = input.mutable_profile();
  profile->set_profile_id(file.expected_profile_id());
  profile->set_working_directory(file.working_directory());
  profile->set_compilation_database(file.compilation_database());
  profile->set_frozen(file.frozen_profile());
  for (const auto &argument : file.compile_arguments())
    profile->add_compile_arguments(argument);
  return input;
}

ctk::match::v1::FileMatchTarget target_from_resolved(
    const ctk::clang_layer::ResolvedFileDescriptor &resolved) {
  ctk::match::v1::FileMatchTarget file;
  file.set_file_path(resolved.descriptor.file_path());
  file.set_working_directory(resolved.descriptor.profile().working_directory());
  file.set_compilation_database(
      resolved.descriptor.profile().compilation_database());
  file.set_expected_profile_id(resolved.descriptor.profile().profile_id());
  file.set_frozen_profile(true);
  for (const auto &argument : resolved.descriptor.profile().compile_arguments())
    file.add_compile_arguments(argument);
  return file;
}

std::string descriptor_identity(
    const ctk::match::v1::InputDescriptor &descriptor) {
  return descriptor.file_path() + "\n" + descriptor.profile().profile_id();
}

std::string new_lease_id() {
  std::array<unsigned char, 16> bytes{};
  if (RAND_bytes(bytes.data(), static_cast<int>(bytes.size())) != 1)
    throw std::runtime_error("file lease identity generation failed");
  bytes[6] = static_cast<unsigned char>((bytes[6] & 0x0f) | 0x40);
  bytes[8] = static_cast<unsigned char>((bytes[8] & 0x3f) | 0x80);
  constexpr char digits[] = "0123456789abcdef";
  std::string id;
  id.reserve(36);
  for (std::size_t i = 0; i < bytes.size(); ++i) {
    if (i == 4 || i == 6 || i == 8 || i == 10)
      id.push_back('-');
    id.push_back(digits[bytes[i] >> 4]);
    id.push_back(digits[bytes[i] & 0x0f]);
  }
  return id;
}
std::string digest_hex(const std::string &value) {
  std::array<unsigned char, SHA256_DIGEST_LENGTH> digest{};
  SHA256(reinterpret_cast<const unsigned char *>(value.data()), value.size(),
         digest.data());
  constexpr char digits[] = "0123456789abcdef";
  std::string output;
  output.reserve(digest.size() * 2);
  for (const auto byte : digest) {
    output.push_back(digits[byte >> 4]);
    output.push_back(digits[byte & 15]);
  }
  return output;
}
} // namespace

struct MatchController::Impl {
  struct FileLeaseRecord {
    std::string owner;
    std::string scope_id;
    std::string identity;
    std::string id;
    std::string root_session_id;
    std::atomic_bool closed{false};
    ctk::match::v1::InputDescriptor input;
    ctk::cache::SnapshotPtr snapshot;
    std::shared_ptr<const ctk::clang_layer::NativeBindingState> state;
  };
  struct FileStore {
    std::mutex mutex;
    std::map<std::string, std::shared_ptr<FileLeaseRecord>> files;
    std::map<std::string, std::string> closed_files;
  };
  CursorSettings settings;
  std::shared_ptr<ResourceManager> resources;
  std::shared_ptr<ctk::clang_layer::IMatchBackend> backend;
  std::shared_ptr<detail::CursorRegistry> registry;
  std::shared_ptr<FileStore> file_store = std::make_shared<FileStore>();
  std::shared_ptr<OperationExecutor> executor;
  const std::chrono::steady_clock::time_point started = std::chrono::steady_clock::now();
  ctk::match::v1::FileInfo file_info(const FileLeaseRecord &lease) const {
    ctk::match::v1::FileInfo info;
    info.set_lease_id(lease.id);
    info.mutable_input()->CopyFrom(lease.input);
    if (lease.snapshot) {
      info.set_snapshot_id(digest_hex(lease.snapshot->canonical_manifest) + ":" +
                           std::to_string(lease.snapshot->generation));
      info.set_accounted_native_bytes(lease.snapshot->estimated_bytes);
      for (const auto &observation : lease.snapshot->inputs)
        if (observation.path == lease.input.file_path()) {
          info.set_source_revision(observation.content_digest);
          break;
        }
    }
    const bool closed = lease.closed.load();
    info.set_explicit_leases(closed ? 0 : 1);
    info.set_state(closed ? ctk::match::v1::FILE_STATE_CLOSED
                                : ctk::match::v1::FILE_STATE_OPEN);
    info.set_resource_scope_id(lease.scope_id);
    info.set_active_work(resources->active_work_for(lease.owner,
                                                    lease.identity));
    info.set_root_session_id(lease.root_session_id);
    if (!lease.root_session_id.empty()) {
      info.set_cursor_count(1);
      info.add_session_ids(lease.root_session_id);
    }
    const auto expires = std::chrono::system_clock::now() + settings.idle_ttl;
    const auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
                        expires.time_since_epoch())
                        .count();
    info.mutable_expires_at()->set_seconds(ns / 1000000000);
    info.mutable_expires_at()->set_nanos(static_cast<int>(ns % 1000000000));
    return info;
  }
  ctk::match::v1::FileInfo cursor_info(
      const detail::ResultCursor &cursor) const {
    ctk::match::v1::FileInfo info;
    info.mutable_input()->CopyFrom(cursor.input);
    info.set_state(ctk::match::v1::FILE_STATE_PINNED);
    info.set_cursor_count(1);
    info.add_session_ids(cursor.id);
    info.set_resource_scope_id(cursor.scope_id);
    info.set_active_work(resources->active_work_for(cursor.owner,
                                                    cursor.input_identity));
    if (cursor.state) {
      const auto snapshot = cursor.state->snapshot();
      if (snapshot) {
        info.set_snapshot_id(digest_hex(snapshot->canonical_manifest) + ":" +
                             std::to_string(snapshot->generation));
        info.set_accounted_native_bytes(snapshot->estimated_bytes);
        for (const auto &observation : snapshot->inputs)
          if (observation.path == cursor.input.file_path()) {
            info.set_source_revision(observation.content_digest);
            break;
          }
      }
    }
    return info;
  }
  ctk::match::v1::FileInfo pin_info(
      const ResourceInputPin &pin) const {
    ctk::match::v1::FileInfo info;
    info.mutable_input()->CopyFrom(pin.input);
    info.set_state(ctk::match::v1::FILE_STATE_PINNED);
    info.set_resource_scope_id(pin.resource_scope_id);
    info.set_active_work(pin.active_work);
    if (pin.snapshot) {
      info.set_snapshot_id(digest_hex(pin.snapshot->canonical_manifest) + ":" +
                           std::to_string(pin.snapshot->generation));
      info.set_accounted_native_bytes(pin.snapshot->estimated_bytes);
      for (const auto &observation : pin.snapshot->inputs)
        if (observation.path == pin.input.file_path()) {
          info.set_source_revision(observation.content_digest);
          break;
        }
    }
    return info;
  }
  Impl(CursorSettings config,
       std::shared_ptr<ctk::clang_layer::IMatchBackend> native,
       std::shared_ptr<OperationExecutor> work)
      : settings(config),
        resources(config.resources ? config.resources
                                  : std::make_shared<ResourceManager>(
                                        ResourceManagerSettings{
                                            static_cast<std::uint64_t>(config.max_cursors),
                                            config.max_memory_bytes,
                                            static_cast<std::uint32_t>(config.workers),
                                            128, config.idle_ttl,
                                            config.idle_ttl})),
        backend(std::move(native)),
        registry(std::make_shared<detail::CursorRegistry>(config)),
        executor(work ? std::move(work)
                      : make_operation_executor(config.workers,
                                                config.pending_requests)) {}
  MatchReply
  run_parse(const std::string &owner, const ParseRequest &request,
            const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint,
            const std::string &work_token) {
    if (!backend)
      return failure(MatchCode::FailedPrecondition,
                     "Clang analysis is disabled");
    registry->find(owner, "");
    ctk::match::v1::InputDescriptor descriptor;
    descriptor.set_file_path(request.file_path());
    auto *profile = descriptor.mutable_profile();
    profile->set_profile_id(request.expected_profile_id());
    profile->set_working_directory(request.working_directory());
    profile->set_compilation_database(request.compilation_database());
    profile->set_frozen(request.frozen_profile());
    for (const auto &argument : request.compile_arguments())
      profile->add_compile_arguments(argument);
    ctk::clang_layer::ResolvedFileDescriptor resolved;
    try {
      resolved = ctk::clang_layer::resolve_file_descriptor(descriptor);
    } catch (const ctk::clang_layer::ProfileMismatch &error) {
      return failure(MatchCode::FailedPrecondition, error.what());
    } catch (const std::length_error &error) {
      return failure(MatchCode::ResourceExhausted, error.what());
    } catch (const std::exception &error) {
      return failure(MatchCode::InvalidArgument, error.what());
    }
    ParseRequest prepared = request;
    prepared.set_file_path(resolved.descriptor.file_path());
    prepared.clear_compile_arguments();
    for (const auto &argument : resolved.descriptor.profile().compile_arguments())
      prepared.add_compile_arguments(argument);
    prepared.set_working_directory(resolved.descriptor.profile().working_directory());
    prepared.set_compilation_database(
        resolved.descriptor.profile().compilation_database());
    prepared.set_frozen_profile(true);
    prepared.set_expected_profile_id(resolved.descriptor.profile().profile_id());
    auto cursor = std::make_shared<detail::ResultCursor>();
    cursor->owner = owner;
    cursor->file_path = resolved.descriptor.file_path();
    cursor->input_identity = descriptor_identity(resolved.descriptor);
    cursor->scope_id = request.resource_scope_id();
    cursor->input = resolved.descriptor;
    std::lock_guard operation(cursor->operation);
    if (cursor->state)
      resources->register_work_snapshot(
          owner, work_token, cursor->input_identity,
          cursor->state->snapshot(), cursor->input);
    auto resource_scope = detail::make_snapshot_scope(
        resources, owner, request.resource_scope_id(), work_token);
    auto result = backend->parse(prepared, checkpoint, settings.results);
    if (result.code != MatchCode::Ok)
      return failure(result.code, result.message);
    if (!result.rows.empty())
      return failure(MatchCode::Internal, "parse returned match rows");
    auto reply = registry->commit(cursor, std::move(result), checkpoint, true);
    if (reply.code == MatchCode::Ok) {
      try {
        const auto id = cursor->id;
        const auto state = cursor->state;
        resources->register_cursor(
            owner, request.resource_scope_id(), id,
            descriptor_identity(resolved.descriptor),
            state ? state->snapshot() : ctk::cache::SnapshotPtr{},
            [registry = registry, owner, id] {
              const auto code = registry->close(owner, id).code;
              return code == MatchCode::Ok || code == MatchCode::NotFound;
            },
            (state ? state->retained_bytes() : 0) +
                cursor->response.ByteSizeLong());
      } catch (const std::exception &error) {
        (void)registry->close(owner, cursor->id);
        return failure(MatchCode::ResourceExhausted, error.what());
      }
    }
    return reply;
  }
  MatchReply run(const std::string &owner, const MatchRequest &request,
                 const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint,
                 const std::string &work_token,
                 const StreamSink *stream_sink = nullptr) {
    if (!backend)
      return failure(MatchCode::FailedPrecondition,
                     "Clang analysis is disabled");
    MatchRequest operation_request = request;
    std::string input_identity;
    const bool fresh_file = request.has_file() || request.has_file_handle();
    std::shared_ptr<FileLeaseRecord> file_lease;
    ctk::match::v1::InputDescriptor file_handle_input;
    std::shared_ptr<const ctk::clang_layer::NativeBindingState> file_handle_state;
    if (request.has_file()) {
      try {
        const auto resolved = ctk::clang_layer::resolve_file_descriptor(
            input_descriptor(request.file()));
        input_identity = descriptor_identity(resolved.descriptor);
        operation_request.mutable_file()->CopyFrom(
            target_from_resolved(resolved));
      } catch (const ctk::clang_layer::ProfileMismatch &error) {
        return failure(MatchCode::FailedPrecondition, error.what());
      } catch (const std::length_error &error) {
        return failure(MatchCode::ResourceExhausted, error.what());
      } catch (const std::exception &error) {
        return failure(MatchCode::InvalidArgument, error.what());
      }
    } else if (request.has_file_handle()) {
      std::lock_guard lock(file_store->mutex);
      const auto found = file_store->files.find(request.file_handle().lease_id());
      if (found == file_store->files.end() || found->second->owner != owner ||
          found->second->closed.load())
        return failure(MatchCode::NotFound, "file lease unavailable");
      file_lease = found->second;
      input_identity = file_lease->identity;
      file_handle_input.CopyFrom(file_lease->input);
      file_handle_state = file_lease->state;
      try {
        resources->claim_snapshot(owner, request.resource_scope_id(),
                                  input_identity, file_lease->snapshot, {},
                                  file_lease->input);
      } catch (const std::exception &error) {
        return failure(MatchCode::FailedPrecondition, error.what());
      }
    }
    std::shared_ptr<detail::ResultCursor> cursor;
    if (fresh_file) {
      // Prune expired cursors before a fresh publication.
      registry->find(owner, "");
      cursor = std::make_shared<detail::ResultCursor>();
      cursor->owner = owner;
      cursor->scope_id = request.resource_scope_id();
      if (request.has_file()) {
        cursor->file_path = operation_request.file().file_path();
        cursor->input_identity = input_identity;
        cursor->input = input_descriptor(operation_request.file());
      } else {
        cursor->file_path = file_handle_input.file_path();
        cursor->input_identity = input_identity;
        cursor->state = std::move(file_handle_state);
        cursor->input = std::move(file_handle_input);
      }
    } else {
      cursor = registry->find(owner, request.has_session()
                                        ? request.session().session_id()
                                        : request.binding().session_id());
      if (!cursor)
        return failure(MatchCode::NotFound, "cursor unavailable");
    }
    std::lock_guard operation(cursor->operation);
    auto resource_scope = detail::make_snapshot_scope(
        resources, owner, request.resource_scope_id(), work_token);
    if (!fresh_file) {
      if (cursor->closed ||
          cursor->deadline <= std::chrono::steady_clock::now())
        return failure(MatchCode::NotFound, "cursor expired or closed");
      const bool guard = request.has_session()
                             ? request.session().has_expected_result_revision()
                             : request.binding().has_expected_result_revision();
      const auto revision = request.has_session()
                                ? request.session().expected_result_revision()
                                : request.binding().expected_result_revision();
      if (guard && revision != cursor->response.result_revision())
        return failure(MatchCode::Aborted, "cursor result revision changed");
      if (request.has_binding()) {
        const auto &target = request.binding();
        bool selected = false;
        const auto scope = target.scope() == BINDING_MATCH_SCOPE_UNSPECIFIED
                               ? BINDING_MATCH_SCOPE_SUBTREE
                               : target.scope();
        for (int i = 0; i < cursor->response.results_size(); ++i) {
          if (target.has_match_index() &&
              target.match_index() != static_cast<std::uint64_t>(i))
            continue;
          const auto &bindings = cursor->response.results(i).bindings();
          const auto found = bindings.find(target.bind());
          if (found == bindings.end())
            continue;
          selected = true;
          const auto &scopes = found->second.supported_scopes();
          if (std::find(scopes.begin(), scopes.end(), scope) == scopes.end())
            return failure(MatchCode::FailedPrecondition,
                           "binding does not support requested scope");
        }
        if (!selected &&
            !(request.preserve_source() && cursor->response.results().empty() &&
              !target.has_match_index()))
          return failure(MatchCode::NotFound, "binding or row unavailable");
      }
    }
    ctk::clang_layer::MatchExecution result;
    if (stream_sink) {
      const ctk::clang_layer::IMatchBackend::RowSink row_sink =
          [this, stream_sink](const MatchResult &row, std::string &message) {
            MatchStreamEvent event;
            *event.mutable_row() = row;
            if (event.ByteSizeLong() > settings.results.max_bytes) {
              message = "match stream event exceeds byte limit (limit " +
                        std::to_string(settings.results.max_bytes) +
                        " bytes); no cursor state committed";
              return MatchCode::ResourceExhausted;
            }
            return (*stream_sink)(event, message);
          };
      result = backend->execute_stream(operation_request, cursor->state, checkpoint,
                                       settings.results, row_sink);
    } else {
      result = backend->execute(operation_request, cursor->state, checkpoint,
                                settings.results);
    }
    if (result.code != MatchCode::Ok)
      return failure(result.code, result.message);
    if (!fresh_file && request.preserve_source()) {
      auto fork = std::make_shared<detail::ResultCursor>();
      fork->owner = owner;
      fork->file_path = cursor->file_path;
      fork->input_identity = cursor->input_identity;
      fork->scope_id = request.resource_scope_id();
      fork->input = cursor->input;
      std::lock_guard fork_operation(fork->operation);
      auto reply = registry->commit(fork, std::move(result), checkpoint, true,
                                   stream_sink != nullptr);
      if (reply.code == MatchCode::Ok) {
        try {
          const auto id = fork->id;
          const auto state = fork->state;
          resources->register_cursor(
              owner, request.resource_scope_id(), id,
              fork->input_identity,
              state ? state->snapshot() : ctk::cache::SnapshotPtr{},
              [registry = registry, owner, id] {
                const auto code = registry->close(owner, id).code;
                return code == MatchCode::Ok || code == MatchCode::NotFound;
              },
              (state ? state->retained_bytes() : 0) +
                  fork->response.ByteSizeLong());
        } catch (const std::exception &error) {
          (void)registry->close(owner, fork->id);
          return failure(MatchCode::ResourceExhausted, error.what());
        }
      }
      if (reply.code == MatchCode::Ok && stream_sink) {
        MatchStreamEvent event;
        auto *completed = event.mutable_completed();
        completed->set_session_id(reply.response.session_id());
        completed->set_result_revision(reply.response.result_revision());
        completed->mutable_expires_at()->CopyFrom(reply.response.expires_at());
        completed->set_row_count(reply.response.results_size());
        std::string message;
        const auto code = (*stream_sink)(event, message);
        if (code != MatchCode::Ok)
          return failure(code, std::move(message));
      }
      return reply;
    }
    auto reply = registry->commit(cursor, std::move(result), checkpoint,
                                 fresh_file, stream_sink != nullptr);
    if (reply.code == MatchCode::Ok && !fresh_file) {
      resources->touch_cursor(
          cursor->scope_id, cursor->id,
          (cursor->state ? cursor->state->retained_bytes() : 0) +
              cursor->response.ByteSizeLong());
    }
    if (reply.code == MatchCode::Ok && fresh_file) {
      try {
        const auto id = cursor->id;
        const auto state = cursor->state;
        resources->register_cursor(
            owner, request.resource_scope_id(), id,
            cursor->input_identity,
            state ? state->snapshot() : ctk::cache::SnapshotPtr{},
            [registry = registry, owner, id] {
              const auto code = registry->close(owner, id).code;
              return code == MatchCode::Ok || code == MatchCode::NotFound;
            },
            (state ? state->retained_bytes() : 0) +
                cursor->response.ByteSizeLong());
      } catch (const std::exception &error) {
        (void)registry->close(owner, cursor->id);
        return failure(MatchCode::ResourceExhausted, error.what());
      }
    }
    if (reply.code == MatchCode::Ok && stream_sink) {
      MatchStreamEvent event;
      auto *completed = event.mutable_completed();
      completed->set_session_id(reply.response.session_id());
      completed->set_result_revision(reply.response.result_revision());
      completed->mutable_expires_at()->CopyFrom(reply.response.expires_at());
      completed->set_row_count(reply.response.results_size());
      std::string message;
      const auto code = (*stream_sink)(event, message);
      if (code != MatchCode::Ok)
        return failure(code, std::move(message));
    }
    return reply;
  }
};

MatchController::MatchController(
    CursorSettings settings,
    std::shared_ptr<ctk::clang_layer::IMatchBackend> backend,
    std::shared_ptr<OperationExecutor> executor) {
  if (settings.max_cursors == 0 || settings.max_memory_bytes == 0 ||
      settings.idle_ttl.count() <= 0 || settings.results.max_rows == 0 ||
      settings.results.max_bytes == 0)
    throw std::invalid_argument("cursor limits and TTL must be positive");
#ifdef CTK_WITH_CLANG
  if (!backend)
    backend = ctk::clang_layer::make_match_backend();
#endif
  impl_ =
      std::make_unique<Impl>(settings, std::move(backend), std::move(executor));
}
MatchController::~MatchController() = default;
ParseReply MatchController::parse(
    const std::string &owner, const ParseRequest &request,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint) {
  const auto invalid = invalid_request(request);
  if (owner.empty() || !invalid.empty())
    return {MatchCode::InvalidArgument,
            owner.empty() ? "caller owner is required" : invalid,
            {}};
  ResourceManager::WorkLease work;
  std::string scope_message;
  const auto scope_status = impl_->resources->begin_work(
      owner, request.resource_scope_id(), work, scope_message);
  if (scope_status != MatchCode::Ok)
    return {scope_status, std::move(scope_message), {}};
  const auto scoped_checkpoint = [checkpoint, &work] {
    return checkpoint() && work.checkpoint();
  };
  auto promise = std::make_shared<std::promise<MatchReply>>();
  const auto work_token = work.token();
  auto future = promise->get_future();
  if (!impl_->executor->enqueue([this, promise, owner, request, scoped_checkpoint,
                                 work_token] {
        try {
          promise->set_value(
              impl_->run_parse(owner, request, scoped_checkpoint, work_token));
        } catch (const std::exception &error) {
          promise->set_value(failure(MatchCode::Internal, error.what()));
        } catch (...) {
          promise->set_value(
              failure(MatchCode::Internal, "native parsing failed"));
        }
      }))
    return {MatchCode::ResourceExhausted,
            "match executor queue is full or stopped",
            {}};
  auto result = future.get();
  ParseReply reply{result.code, std::move(result.message), {}};
  if (result.code == MatchCode::Ok) {
    reply.response.set_session_id(result.response.session_id());
    reply.response.set_result_revision(result.response.result_revision());
    reply.response.mutable_expires_at()->Swap(
        result.response.mutable_expires_at());
    try {
      auto resolved = ctk::clang_layer::resolve_file_descriptor(
          [&] {
            InputDescriptor descriptor;
            descriptor.set_file_path(request.file_path());
            auto *profile = descriptor.mutable_profile();
            profile->set_profile_id(request.expected_profile_id());
            profile->set_working_directory(request.working_directory());
            profile->set_compilation_database(request.compilation_database());
            profile->set_frozen(request.frozen_profile());
            for (const auto &argument : request.compile_arguments())
              profile->add_compile_arguments(argument);
            return descriptor;
          }());
      auto cursor = impl_->registry->find(owner, result.response.session_id());
      if (!cursor || !cursor->state)
        throw std::runtime_error("parsed cursor expired before lease publication");
      auto lease = std::make_shared<Impl::FileLeaseRecord>();
      lease->owner = owner;
      lease->scope_id = request.resource_scope_id();
      lease->identity = descriptor_identity(resolved.descriptor);
      lease->id = new_lease_id();
      lease->root_session_id = cursor->id;
      lease->input = resolved.descriptor;
      lease->state = cursor->state;
      lease->snapshot = cursor->state->snapshot();
      const auto lease_id = lease->id;
      std::weak_ptr<Impl::FileLeaseRecord> weak = lease;
      impl_->resources->register_file_lease(
          owner, lease->scope_id, lease->id, lease->identity, lease->snapshot,
          [store = impl_->file_store, weak] {
            if (auto locked = weak.lock()) {
              locked->closed.store(true);
              {
                std::lock_guard lock(store->mutex);
                store->files.erase(locked->id);
                locked->state.reset();
                locked->snapshot.reset();
              }
            }
            return true;
          });
      {
        std::lock_guard lock(impl_->file_store->mutex);
        impl_->file_store->files.emplace(lease->id, std::move(lease));
      }
      reply.response.set_file_lease_id(lease_id);
    } catch (const std::exception &error) {
      (void)impl_->registry->close(owner, result.response.session_id());
      return {MatchCode::ResourceExhausted, error.what(), {}};
    }
  }
  return reply;
}
MatchReply MatchController::match(
    const std::string &owner, const MatchRequest &request,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint) {
  const auto invalid = invalid_request(request);
  if (owner.empty() || !invalid.empty())
    return failure(MatchCode::InvalidArgument,
                   owner.empty() ? "caller owner is required" : invalid);
  ResourceManager::WorkLease work;
  std::string scope_message;
  const auto scope_status = impl_->resources->begin_work(
      owner, request.resource_scope_id(), work, scope_message);
  if (scope_status != MatchCode::Ok)
    return failure(scope_status, std::move(scope_message));
  const auto scoped_checkpoint = [checkpoint, &work] {
    return checkpoint() && work.checkpoint();
  };
  auto promise = std::make_shared<std::promise<MatchReply>>();
  const auto work_token = work.token();
  auto future = promise->get_future();
  if (!impl_->executor->enqueue([this, promise, owner, request, scoped_checkpoint,
                                 work_token] {
        try {
          promise->set_value(
              impl_->run(owner, request, scoped_checkpoint, work_token));
        } catch (const std::exception &error) {
          promise->set_value(failure(MatchCode::Internal, error.what()));
        } catch (...) {
          promise->set_value(
              failure(MatchCode::Internal, "native matching failed"));
        }
      }))
    return failure(MatchCode::ResourceExhausted,
                   "match executor queue is full or stopped");
  return future.get();
}
MatchReply MatchController::stream_match(
    const std::string &owner, const MatchRequest &request,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint,
    const StreamSink &sink) {
  const auto invalid = invalid_request(request);
  if (owner.empty() || !invalid.empty())
    return failure(MatchCode::InvalidArgument,
                   owner.empty() ? "caller owner is required" : invalid);
  ResourceManager::WorkLease work;
  std::string scope_message;
  const auto scope_status = impl_->resources->begin_work(
      owner, request.resource_scope_id(), work, scope_message);
  if (scope_status != MatchCode::Ok)
    return failure(scope_status, std::move(scope_message));
  const auto scoped_checkpoint = [checkpoint, &work] {
    return checkpoint() && work.checkpoint();
  };
  // Reject an event cap too small for any valid completion before work can
  // commit. Maximal field widths make this a conservative wire-size bound.
  MatchStreamEvent maximum_completion;
  auto *completed = maximum_completion.mutable_completed();
  completed->set_session_id("00000000-0000-4000-8000-000000000000");
  completed->set_result_revision(std::numeric_limits<std::uint64_t>::max());
  completed->mutable_expires_at()->set_seconds(253402300799LL);
  completed->mutable_expires_at()->set_nanos(999999999);
  completed->set_row_count(std::numeric_limits<std::uint64_t>::max());
  if (maximum_completion.ByteSizeLong() > impl_->settings.results.max_bytes)
    return failure(MatchCode::ResourceExhausted,
                   "match completion event exceeds byte limit; no cursor "
                   "state committed");
  auto promise = std::make_shared<std::promise<MatchReply>>();
  const auto work_token = work.token();
  auto future = promise->get_future();
  if (!impl_->executor->enqueue(
          [this, promise, owner, request, scoped_checkpoint, sink, work_token] {
            try {
              promise->set_value(
                  impl_->run(owner, request, scoped_checkpoint, work_token,
                             &sink));
            } catch (const std::exception &error) {
              promise->set_value(failure(MatchCode::Internal, error.what()));
            } catch (...) {
              promise->set_value(
                  failure(MatchCode::Internal, "native matching failed"));
            }
          }))
    return failure(MatchCode::ResourceExhausted,
                   "match executor queue is full or stopped");
  return future.get();
}
MatchReply MatchController::close(const std::string &owner,
                                  const std::string &id) {
  const auto cursor = impl_->registry->find(owner, id);
  const auto reply = impl_->registry->close(owner, id);
  if (reply.code == MatchCode::Ok) {
    if (cursor)
      impl_->resources->unregister_cursor(cursor->scope_id, id);
    CloseFileRequest request;
    request.set_session_id(id);
    CloseFileResponse response;
    (void)close_file(owner, request, response);
  }
  return reply;
}
void MatchController::stop_admission() { impl_->executor->stop_admission(); }

ListSessionsResponse MatchController::list_sessions(const std::string &owner) {
  return impl_->registry->list(owner);
}
MatchReply MatchController::attach_session(const std::string &owner,
                                           const std::string &id,
                                           SessionInfo &response) {
  if (owner.empty())
    return failure(MatchCode::InvalidArgument, "caller owner is required");
  auto reply = impl_->registry->attach(owner, id, response);
  if (reply.code == MatchCode::Ok) {
    const auto cursor = impl_->registry->find(owner, id);
    if (cursor)
      impl_->resources->touch_cursor(
          cursor->scope_id, cursor->id,
          (cursor->state ? cursor->state->retained_bytes() : 0) +
              cursor->response.ByteSizeLong());
  }
  return reply;
}

DiscoverFilesResponse MatchController::discover_files(
    const DiscoverFilesRequest &request,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint,
    MatchCode &code, std::string &message) {
  try {
    auto response = ctk::clang_layer::discover_file_descriptors(
        request, checkpoint ? checkpoint : [] { return true; });
    code = MatchCode::Ok;
    message.clear();
    return response;
  } catch (const std::length_error &error) {
    code = MatchCode::ResourceExhausted;
    message = error.what();
  } catch (const std::exception &error) {
    code = std::string(error.what()).find("cancelled") != std::string::npos
               ? MatchCode::Cancelled
               : MatchCode::InvalidArgument;
    message = error.what();
  }
  return {};
}

MatchCode MatchController::open_resource_scope(
    const std::string &owner, const OpenResourceScopeRequest &request,
    ResourceScopeInfo &response, std::string &message) {
  std::vector<ResourceInputReservation> inputs;
  inputs.reserve(request.inputs_size());
  try {
    for (const auto &input : request.inputs()) {
      auto resolved = ctk::clang_layer::resolve_file_descriptor(input);
      inputs.push_back({descriptor_identity(resolved.descriptor),
                        resolved.descriptor.estimated_parse_bytes()});
    }
  } catch (const ctk::clang_layer::ProfileMismatch &error) {
    message = error.what();
    return MatchCode::FailedPrecondition;
  } catch (const std::length_error &error) {
    message = error.what();
    return MatchCode::ResourceExhausted;
  } catch (const std::exception &error) {
    message = error.what();
    return MatchCode::InvalidArgument;
  }
  return impl_->resources->open_scope(owner, request, inputs, response,
                                      message);
}

MatchCode MatchController::describe_resource_scope(
    const std::string &owner, const std::string &id,
    ResourceScopeInfo &response) {
  return impl_->resources->describe_scope(owner, id, response);
}
MatchCode MatchController::cancel_resource_scope(
    const std::string &owner, const std::string &id,
    ResourceScopeInfo &response) {
  return impl_->resources->cancel_scope(owner, id, response);
}
MatchCode MatchController::release_resource_scope(
    const std::string &owner, const std::string &id,
    ResourceScopeInfo &response) {
  return impl_->resources->release_scope(owner, id, response);
}
ResourceStatusResponse MatchController::resource_status() {
  ResourceStatusResponse result;
  const auto cache = impl_->backend ? impl_->backend->resources()
                                    : CacheResources{};
  result = impl_->resources->status(cache,
                                    ctk::platform::resident_memory_bytes());
  result.set_max_result_rows(impl_->settings.results.max_rows);
  result.set_max_result_bytes(impl_->settings.results.max_bytes);
  result.set_max_manifest_inputs(
      ctk::clang_layer::max_manifest_inputs);
  result.set_max_manifest_bytes(
      ctk::clang_layer::max_manifest_bytes);
  result.set_queued_work(impl_->executor->pending_count());
  return result;
}

MatchCode MatchController::open_file(
    const std::string &owner, const OpenFileRequest &request,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint,
    FileInfo &response, std::string &message) {
  if (owner.empty()) {
    message = "caller owner is required";
    return MatchCode::InvalidArgument;
  }
  if (!impl_->backend) {
    message = "Clang analysis is disabled";
    return MatchCode::FailedPrecondition;
  }
  ctk::clang_layer::ResolvedFileDescriptor resolved;
  try {
    resolved = ctk::clang_layer::resolve_file_descriptor(request.input());
  } catch (const ctk::clang_layer::ProfileMismatch &error) {
    message = error.what();
    return MatchCode::FailedPrecondition;
  } catch (const std::length_error &error) {
    message = error.what();
    return MatchCode::ResourceExhausted;
  } catch (const std::exception &error) {
    message = error.what();
    return MatchCode::InvalidArgument;
  }
  ResourceManager::WorkLease acquired_work;
  const auto admission = impl_->resources->begin_work(
      owner, request.resource_scope_id(), acquired_work, message);
  if (admission != MatchCode::Ok)
    return admission;
  auto work = std::make_shared<ResourceManager::WorkLease>(
      std::move(acquired_work));
  const auto scoped_checkpoint = [checkpoint, work] {
    return (!checkpoint || checkpoint()) && work->checkpoint();
  };
  ParseRequest parse;
  parse.set_file_path(resolved.file.path);
  parse.set_working_directory(resolved.file.working_directory);
  parse.set_compilation_database(resolved.file.compilation_database);
  parse.set_frozen_profile(true);
  parse.set_expected_profile_id(resolved.descriptor.profile().profile_id());
  for (const auto &argument : resolved.file.compile_arguments)
    parse.add_compile_arguments(argument);
  auto promise = std::make_shared<std::promise<ctk::clang_layer::MatchExecution>>();
  auto future = promise->get_future();
  if (!impl_->executor->enqueue(
          [this, promise, parse, scoped_checkpoint, owner, work,
           scope_id = request.resource_scope_id()] {
            try {
              auto native_scope = detail::make_snapshot_scope(
                  impl_->resources, owner, scope_id, work->token());
              promise->set_value(impl_->backend->parse(
                  parse, scoped_checkpoint, impl_->settings.results));
            } catch (const std::exception &error) {
              promise->set_value({MatchCode::Internal, error.what(), {}, {}});
            } catch (...) {
              promise->set_value(
                  {MatchCode::Internal, "file open failed", {}, {}});
            }
          })) {
    message = "match executor queue is full or stopped";
    return MatchCode::ResourceExhausted;
  }
  auto parsed = future.get();
  if (parsed.code != MatchCode::Ok) {
    message = parsed.message;
    return parsed.code;
  }
  if (!parsed.state || !parsed.state->snapshot()) {
    message = "native parser returned no file snapshot";
    return MatchCode::Internal;
  }
  auto lease = std::make_shared<Impl::FileLeaseRecord>();
  lease->owner = owner;
  lease->scope_id = request.resource_scope_id();
  lease->identity = descriptor_identity(resolved.descriptor);
  lease->id = new_lease_id();
  lease->input = resolved.descriptor;
  lease->snapshot = parsed.state->snapshot();
  lease->state = std::move(parsed.state);
  std::weak_ptr<Impl::FileLeaseRecord> weak = lease;
  try {
    impl_->resources->register_file_lease(
        owner, lease->scope_id, lease->id, lease->identity, lease->snapshot,
        [store = impl_->file_store, weak] {
          if (auto locked = weak.lock()) {
            locked->closed.store(true);
            {
              std::lock_guard lock(store->mutex);
              store->files.erase(locked->id);
              locked->state.reset();
              locked->snapshot.reset();
            }
          }
          return true;
        });
  } catch (const std::exception &error) {
    message = error.what();
    return MatchCode::ResourceExhausted;
  }
  {
    std::lock_guard lock(impl_->file_store->mutex);
    impl_->file_store->files.emplace(lease->id, lease);
  }
  response = impl_->file_info(*lease);
  message.clear();
  return MatchCode::Ok;
}

ListFilesResponse MatchController::list_files(const std::string &owner) {
  ListFilesResponse response;
  std::map<std::string, int> by_session;
  std::set<std::pair<std::string, std::string>> listed;
  const auto remember = [&](const ctk::match::v1::FileInfo &info) {
    listed.emplace(descriptor_identity(info.input()), info.snapshot_id());
  };
  {
    std::lock_guard lock(impl_->file_store->mutex);
    for (auto it = impl_->file_store->files.begin();
         it != impl_->file_store->files.end();) {
      const auto &lease = it->second;
      if (lease->closed.load()) {
        it = impl_->file_store->files.erase(it);
        continue;
      }
      if (lease->owner == owner) {
        auto *info = response.add_files();
        info->CopyFrom(impl_->file_info(*lease));
        remember(*info);
        if (!lease->root_session_id.empty())
          by_session.emplace(lease->root_session_id, response.files_size() - 1);
      }
      ++it;
    }
  }
  const auto sessions = impl_->registry->list(owner);
  for (const auto &session : sessions.sessions()) {
    if (const auto paired = by_session.find(session.session_id());
        paired != by_session.end())
      continue;
    const auto cursor = impl_->registry->find(owner, session.session_id());
    if (cursor) {
      response.add_files()->CopyFrom(impl_->cursor_info(*cursor));
      remember(response.files(response.files_size() - 1));
    }
  }
  for (const auto &pin : impl_->resources->input_pins(owner)) {
    auto info = impl_->pin_info(pin);
    if (listed.emplace(descriptor_identity(info.input()), info.snapshot_id())
            .second)
      response.add_files()->CopyFrom(info);
  }
  return response;
}

MatchCode MatchController::describe_file(const std::string &owner,
                                         const DescribeFileRequest &request,
                                         FileInfo &response) {
  std::lock_guard lock(impl_->file_store->mutex);
  for (const auto &[id, lease] : impl_->file_store->files) {
    if (lease->owner != owner || lease->closed.load())
      continue;
    if ((request.has_lease_id() && id == request.lease_id()) ||
        (request.has_session_id() &&
         lease->root_session_id == request.session_id())) {
      response = impl_->file_info(*lease);
      return MatchCode::Ok;
    }
  }
  if (request.has_session_id()) {
    const auto cursor = impl_->registry->find(owner, request.session_id());
    if (cursor) {
      response = impl_->cursor_info(*cursor);
      return MatchCode::Ok;
    }
  }
  return MatchCode::NotFound;
}

MatchCode MatchController::close_file(const std::string &owner,
                                      const CloseFileRequest &request,
                                      CloseFileResponse &response) {
  std::vector<std::shared_ptr<Impl::FileLeaseRecord>> closing;
  {
    std::lock_guard lock(impl_->file_store->mutex);
    for (auto it = impl_->file_store->files.begin();
         it != impl_->file_store->files.end();) {
      auto lease = it->second;
      const bool match = lease->owner == owner &&
          ((request.has_lease_id() && lease->id == request.lease_id()) ||
           (request.has_session_id() &&
            lease->root_session_id == request.session_id()));
      if (!match) {
        ++it;
        continue;
      }
      lease->closed.store(true);
      impl_->file_store->closed_files.insert_or_assign(lease->id, owner);
      if (impl_->file_store->closed_files.size() > 10000)
        impl_->file_store->closed_files.erase(
            impl_->file_store->closed_files.begin());
      closing.push_back(std::move(lease));
      it = impl_->file_store->files.erase(it);
    }
  }
  if (request.has_session_id()) {
    const auto cursor = impl_->registry->find(owner, request.session_id());
    const auto closed = impl_->registry->close(owner, request.session_id());
    if (closed.code != MatchCode::Ok && closing.empty())
      return closed.code;
    if (closed.code == MatchCode::Ok) {
      response.set_closed_cursors(1);
      impl_->resources->unregister_cursor(
          cursor ? cursor->scope_id : std::string{}, request.session_id());
    }
  }
  for (const auto &lease : closing) {
    impl_->resources->unregister_file_lease(lease->scope_id, lease->id);
    response.set_released_leases(response.released_leases() + 1);
    if (!lease->root_session_id.empty()) {
      const auto closed = impl_->registry->close(owner, lease->root_session_id);
      if (closed.code == MatchCode::Ok) {
        response.set_closed_cursors(response.closed_cursors() + 1);
        impl_->resources->unregister_cursor(lease->scope_id,
                                            lease->root_session_id);
      }
    }
  }
  if (closing.empty() && request.has_lease_id()) {
    std::lock_guard lock(impl_->file_store->mutex);
    const auto closed = impl_->file_store->closed_files.find(request.lease_id());
    if (closed != impl_->file_store->closed_files.end() && closed->second == owner)
      return MatchCode::Ok;
  }
  const auto remaining = list_files(owner);
  for (const auto &file : remaining.files())
    response.add_remaining()->CopyFrom(file);
  return closing.empty() && !request.has_session_id() ? MatchCode::NotFound
                                                      : MatchCode::Ok;
}

MatchCode MatchController::close_all_files(const std::string &owner,
                                           CloseFileResponse &response) {
  CloseFileRequest request;
  std::vector<std::string> ids;
  {
    std::lock_guard lock(impl_->file_store->mutex);
    for (const auto &[id, lease] : impl_->file_store->files)
      if (lease->owner == owner && !lease->closed.load())
        ids.push_back(id);
  }
  for (const auto &id : ids) {
    request.set_lease_id(id);
    CloseFileResponse one;
    const auto code = close_file(owner, request, one);
    if (code != MatchCode::Ok && code != MatchCode::NotFound)
      return code;
    response.set_released_leases(response.released_leases() +
                                 one.released_leases());
    response.set_closed_cursors(response.closed_cursors() +
                                one.closed_cursors());
    request.clear_handle();
  }
  for (const auto &session : impl_->registry->list(owner).sessions()) {
    request.set_session_id(session.session_id());
    CloseFileResponse one;
    const auto code = close_file(owner, request, one);
    if (code != MatchCode::Ok && code != MatchCode::NotFound)
      return code;
    response.set_released_leases(response.released_leases() +
                                 one.released_leases());
    response.set_closed_cursors(response.closed_cursors() +
                                one.closed_cursors());
    request.clear_handle();
  }
  for (const auto &file : list_files(owner).files())
    response.add_remaining()->CopyFrom(file);
  return MatchCode::Ok;
}

MatchCode MatchController::refresh_file(
    const std::string &owner, const RefreshFileRequest &request,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint,
    FileInfo &response, std::string &message) {
  FileInfo previous;
  DescribeFileRequest describe;
  if (request.has_lease_id())
    describe.set_lease_id(request.lease_id());
  else if (request.has_session_id())
    describe.set_session_id(request.session_id());
  else
    return MatchCode::InvalidArgument;
  const auto found = describe_file(owner, describe, previous);
  if (found != MatchCode::Ok)
    return found;
  OpenFileRequest open;
  open.mutable_input()->CopyFrom(previous.input());
  open.set_resource_scope_id(request.resource_scope_id().empty()
                                 ? previous.resource_scope_id()
                                 : request.resource_scope_id());
  const auto refreshed = open_file(owner, open, checkpoint, response, message);
  if (refreshed != MatchCode::Ok)
    return refreshed;
  return MatchCode::Ok;
}
ServerStatusResponse MatchController::server_status() {
  ServerStatusResponse response;
  response.set_uptime_ms(std::chrono::duration_cast<std::chrono::milliseconds>(
      std::chrono::steady_clock::now() - impl_->started).count());
  if (const auto rss = ctk::platform::resident_memory_bytes())
    response.set_resident_memory_bytes(*rss);
  const auto [count, bytes] = impl_->registry->usage();
  response.set_active_sessions(count);
  response.set_retained_memory_bytes(bytes);
  response.set_max_sessions(impl_->settings.max_cursors);
  response.set_max_retained_memory_bytes(impl_->settings.max_memory_bytes);
  if (impl_->backend)
    response.mutable_cache()->CopyFrom(impl_->backend->resources());
  return response;
}
MatchReply MatchController::prune_caches(const PruneCachesRequest &request,
                                        PruneCachesResponse &response) {
  if (!request.memory() && !request.disk())
    return failure(MatchCode::InvalidArgument, "select memory and/or disk caches");
  if (!impl_->backend)
    return failure(MatchCode::FailedPrecondition, "Clang analysis is disabled");
  try {
    response.mutable_before()->CopyFrom(impl_->backend->resources());
    if ((request.memory() && !response.before().memory_available()) ||
        (request.disk() && !response.before().storage_available()))
      return failure(MatchCode::FailedPrecondition, "selected cache is unavailable");
    impl_->backend->prune_caches(request.memory(), request.disk());
    response.mutable_after()->CopyFrom(impl_->backend->resources());
    return {};
  } catch (const std::exception &error) {
    return failure(MatchCode::Internal, error.what());
  }
}
} // namespace ctk::application
