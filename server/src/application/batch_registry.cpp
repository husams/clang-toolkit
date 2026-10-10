#include "ctk/application/batch_registry.hpp"

#include "analysis/v1/script_value.pb.h"
#include "ctk/clang/file_discovery.hpp"
#include "ctk/platform/durable_file.hpp"
#include "ctk/script/engine.hpp"
#include "ctk/script/error.hpp"
#include "ctk/script/value.hpp"

#include <google/protobuf/struct.pb.h>
#include <google/protobuf/util/json_util.h>
#include <google/protobuf/util/message_differencer.h>
#include <openssl/evp.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <condition_variable>
#include <fstream>
#include <functional>
#include <iomanip>
#include <map>
#include <mutex>
#include <queue>
#include <random>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string_view>
#include <system_error>
#include <thread>
#include <unordered_map>

namespace ctk::application {
using Code = ctk::clang_layer::MatchCode;
namespace {
using namespace ctk::analysis::v1;
using Code = ctk::clang_layer::MatchCode;

std::string sha256(std::string_view bytes) {
  std::array<unsigned char, EVP_MAX_MD_SIZE> digest{};
  unsigned int length = 0;
  EVP_MD_CTX *context = EVP_MD_CTX_new();
  if (!context)
    throw std::runtime_error("could not allocate digest context");
  const bool ok = EVP_DigestInit_ex(context, EVP_sha256(), nullptr) == 1 &&
                  EVP_DigestUpdate(context, bytes.data(), bytes.size()) == 1 &&
                  EVP_DigestFinal_ex(context, digest.data(), &length) == 1;
  EVP_MD_CTX_free(context);
  if (!ok)
    throw std::runtime_error("could not compute SHA-256 digest");
  static constexpr char digits[] = "0123456789abcdef";
  std::string result;
  result.reserve(length * 2);
  for (unsigned int i = 0; i < length; ++i) {
    result.push_back(digits[digest[i] >> 4]);
    result.push_back(digits[digest[i] & 0x0f]);
  }
  return result;
}

std::string random_id() {
  std::random_device random;
  std::array<unsigned char, 16> bytes{};
  for (auto &byte : bytes)
    byte = static_cast<unsigned char>(random());
  bytes[6] = static_cast<unsigned char>((bytes[6] & 0x0f) | 0x40);
  bytes[8] = static_cast<unsigned char>((bytes[8] & 0x3f) | 0x80);
  static constexpr char digits[] = "0123456789abcdef";
  std::string result;
  result.reserve(36);
  for (std::size_t i = 0; i < bytes.size(); ++i) {
    if (i == 4 || i == 6 || i == 8 || i == 10)
      result.push_back('-');
    result.push_back(digits[bytes[i] >> 4]);
    result.push_back(digits[bytes[i] & 0x0f]);
  }
  return result;
}

std::filesystem::path input_path(const ctk::match::v1::InputDescriptor &input) {
  std::filesystem::path path(input.file_path());
  if (path.is_relative() && !input.profile().working_directory().empty())
    path = std::filesystem::path(input.profile().working_directory()) / path;
  return path.lexically_normal();
}

std::string digest_file(const std::filesystem::path &path) {
  std::ifstream stream(path, std::ios::binary);
  if (!stream)
    throw std::runtime_error("cannot read batch input: " + path.string());
  EVP_MD_CTX *context = EVP_MD_CTX_new();
  if (!context)
    throw std::runtime_error("could not allocate digest context");
  if (EVP_DigestInit_ex(context, EVP_sha256(), nullptr) != 1) {
    EVP_MD_CTX_free(context);
    throw std::runtime_error("could not initialize source digest");
  }
  std::array<char, 64 * 1024> buffer{};
  while (stream) {
    stream.read(buffer.data(), static_cast<std::streamsize>(buffer.size()));
    const auto count = stream.gcount();
    if (count > 0 && EVP_DigestUpdate(context, buffer.data(),
                                      static_cast<std::size_t>(count)) != 1) {
      EVP_MD_CTX_free(context);
      throw std::runtime_error("could not update source digest");
    }
  }
  if (!stream.eof()) {
    EVP_MD_CTX_free(context);
    throw std::runtime_error("could not read batch input: " + path.string());
  }
  std::array<unsigned char, EVP_MAX_MD_SIZE> digest{};
  unsigned int length = 0;
  const auto ok = EVP_DigestFinal_ex(context, digest.data(), &length) == 1;
  EVP_MD_CTX_free(context);
  if (!ok)
    throw std::runtime_error("could not finalize source digest");
  static constexpr char digits[] = "0123456789abcdef";
  std::string result;
  result.reserve(length * 2);
  for (unsigned int i = 0; i < length; ++i) {
    result.push_back(digits[digest[i] >> 4]);
    result.push_back(digits[digest[i] & 0x0f]);
  }
  return result;
}

std::string
closure_revision(const std::string &profile_id,
                 const std::vector<ScriptSourceRevision> &observations) {
  auto sorted = observations;
  std::sort(sorted.begin(), sorted.end(),
            [](const auto &left, const auto &right) {
              return std::tie(left.path, left.kind, left.content_digest,
                              left.validation_context) <
                     std::tie(right.path, right.kind, right.content_digest,
                              right.validation_context);
            });
  std::string material = profile_id;
  for (const auto &item : sorted) {
    std::string stable_context = item.validation_context;
    if (!stable_context.empty()) {
      google::protobuf::Struct context;
      if (!google::protobuf::util::JsonStringToMessage(stable_context, &context)
               .ok())
        throw std::runtime_error("invalid source validation context");
      const auto &fields = context.fields();
      auto append_field = [&stable_context](std::string_view value) {
        stable_context.append(std::to_string(value.size()));
        stable_context.push_back(':');
        stable_context.append(value);
      };
      stable_context.clear();
      for (const auto *name : {"format", "lookup_path", "real_path"}) {
        const auto found = fields.find(name);
        append_field(found == fields.end() ? "" : found->second.string_value());
      }
      for (const auto *name : {"error", "enumerated"}) {
        const auto found = fields.find(name);
        if (found == fields.end()) {
          append_field("");
        } else if (std::string_view(name) == "error") {
          append_field(std::to_string(found->second.number_value()));
        } else {
          append_field(found->second.bool_value() ? "true" : "false");
        }
      }
      std::vector<std::string> aliases;
      if (const auto found = fields.find("aliases");
          found != fields.end() && found->second.has_list_value()) {
        for (const auto &alias : found->second.list_value().values())
          aliases.push_back(alias.string_value());
      }
      std::sort(aliases.begin(), aliases.end());
      for (const auto &alias : aliases)
        append_field(alias);
    }
    const std::array<const std::string *, 4> fields{
        &item.path, &item.kind, &item.content_digest, &stable_context};
    for (const auto *field : fields) {
      material.append(std::to_string(field->size()));
      material.push_back(':');
      material.append(*field);
    }
  }
  return sha256(material);
}

std::string read_bytes(const std::filesystem::path &path) {
  std::ifstream stream(path, std::ios::binary);
  return {std::istreambuf_iterator<char>(stream), {}};
}

std::uint64_t tree_size(const std::filesystem::path &root) {
  std::uint64_t total = 0;
  std::error_code error;
  if (!std::filesystem::exists(root, error))
    return 0;
  for (std::filesystem::recursive_directory_iterator it(root, error), end;
       !error && it != end; it.increment(error)) {
    if (it->is_regular_file(error))
      total += it->file_size(error);
  }
  return total;
}

std::string serialized(const google::protobuf::MessageLite &message) {
  std::string bytes;
  if (!message.SerializeToString(&bytes))
    throw std::runtime_error("could not serialize durable batch record");
  return bytes;
}

void set_state(BatchRun &run, const char *state) { run.set_state(state); }

bool terminal_group(const BatchGroup &group) {
  return group.state() == "completed" || group.state() == "failed" ||
         group.state() == "cancelled" || group.state() == "unknown";
}

class ScopeExit final {
public:
  explicit ScopeExit(std::function<void()> action)
      : action_(std::move(action)) {}
  ~ScopeExit() {
    if (action_)
      action_();
  }
  void dismiss() { action_ = {}; }

private:
  std::function<void()> action_;
};

std::uint64_t value_item_count(const ScriptValue &value) {
  std::uint64_t count = 1;
  switch (value.value_case()) {
  case ScriptValue::kList:
    for (const auto &child : value.list().values())
      count += value_item_count(child);
    break;
  case ScriptValue::kObject:
    for (const auto &[key, child] : value.object().fields()) {
      (void)key;
      count += value_item_count(child);
    }
    break;
  case ScriptValue::kMatches:
    count += value.matches().rows_size();
    break;
  case ScriptValue::kTraversal:
    count += value.traversal().nodes_size();
    break;
  case ScriptValue::kCfg:
    count += value.cfg().graphs_size();
    break;
  case ScriptValue::kCallGraph:
    count += value.call_graph().nodes_size();
    break;
  default:
    break;
  }
  return count;
}

std::uint64_t response_item_count(const ScriptResponse &response) {
  std::uint64_t count = response.emissions_size();
  for (const auto &emission : response.emissions())
    count += value_item_count(emission.value());
  return count;
}

} // namespace

struct BatchRegistry::Impl {
  struct Record {
    BatchRun run;
    std::string owner_hash;
    std::filesystem::path path;
    std::atomic_bool cancel_requested{false};
  };

  ScriptController &scripts;
  std::shared_ptr<ResourceManager> resources;
  std::filesystem::path root;
  BatchRegistryLimits limits;
  mutable std::mutex mutex;
  std::condition_variable changed;
  std::unordered_map<std::string, std::shared_ptr<Record>> records;
  std::unordered_map<std::string, std::string> request_index;
  std::queue<std::string> queue;
  bool stopping{false};
  bool journal_failed{false};
  std::thread worker;

  Impl(ScriptController &controller, std::shared_ptr<ResourceManager> manager,
       std::filesystem::path storage_root, BatchRegistryLimits configured)
      : scripts(controller), resources(std::move(manager)),
        root(std::filesystem::absolute(std::move(storage_root)) / "batches"),
        limits(configured) {
    recover();
    worker = std::thread([this] { work_loop(); });
  }

  std::string owner_key(const std::string &owner) const {
    return sha256(owner);
  }

  std::filesystem::path owner_directory(const std::string &key) const {
    return root / key;
  }

  std::string request_key(const std::string &owner_hash,
                          const std::string &request_id) const {
    return owner_hash + ":" + request_id;
  }

  std::uint64_t persisted_bytes_locked() const { return tree_size(root); }

  void trip_journal_locked() {
    journal_failed = true;
    for (auto &[id, record] : records) {
      (void)id;
      if (record->run.state() == "queued" || record->run.state() == "running")
        record->cancel_requested.store(true);
    }
  }

  Code ensure_journal_healthy_locked(std::string &message) const {
    if (!journal_failed)
      return Code::Ok;
    message = "durable batch journal is fail-closed until server restart";
    return Code::Internal;
  }

  void persist_run_locked(Record &record, const BatchRun &run) {
    auto bytes = serialized(run);
    if (bytes.size() > limits.max_manifest_bytes)
      throw std::length_error("batch manifest/report exceeds byte limit");
    std::uint64_t existing_size = 0;
    std::error_code size_error;
    if (std::filesystem::exists(record.path, size_error))
      existing_size = std::filesystem::file_size(record.path, size_error);
    if (persisted_bytes_locked() -
            std::min(persisted_bytes_locked(), existing_size) + bytes.size() >
        limits.max_persisted_bytes)
      throw std::length_error("durable batch registry storage limit exceeded");
    try {
      if (limits.journal_write)
        limits.journal_write(record.path, bytes);
      else
        ctk::platform::durable_atomic_write(record.path, bytes);
    } catch (...) {
      trip_journal_locked();
      throw;
    }
  }

  void persist_locked(Record &record) {
    persist_run_locked(record, record.run);
  }

  Code lookup_locked(const std::string &run_id, const std::string &owner,
                     std::shared_ptr<Record> &record,
                     std::string &message) const {
    auto found = records.find(run_id);
    if (found == records.end()) {
      message = "batch run was not found";
      return Code::NotFound;
    }
    if (found->second->owner_hash != owner_key(owner)) {
      message = "batch run belongs to another caller";
      return Code::NotFound;
    }
    record = found->second;
    return Code::Ok;
  }

  void copy_response(const Record &record, BatchRun &response) const {
    response.CopyFrom(record.run);
  }

  void queue_locked(const std::shared_ptr<Record> &record) {
    queue.push(record->run.run_id());
    changed.notify_one();
  }

  std::uint32_t active_runs_locked() const {
    std::uint32_t count = 0;
    for (const auto &[id, record] : records) {
      (void)id;
      if (record->run.state() == "queued" || record->run.state() == "running")
        ++count;
    }
    return count;
  }

  void recover() {
    std::error_code error;
    if (!std::filesystem::exists(root, error))
      return;
    for (std::filesystem::recursive_directory_iterator it(root, error), end;
         !error && it != end; it.increment(error)) {
      if (!it->is_regular_file(error) || it->path().extension() != ".pb")
        continue;
      const auto bytes = read_bytes(it->path());
      auto record = std::make_shared<Record>();
      if (!record->run.ParseFromString(bytes) || record->run.run_id().empty())
        continue;
      record->path = it->path();
      record->owner_hash = it->path().parent_path().filename().string();
      bool interrupted = false;
      if (record->run.state() == "running" || record->run.state() == "queued") {
        record->run.set_state("interrupted");
        for (auto &group : *record->run.mutable_groups()) {
          if (group.state() == "running") {
            group.set_state("unknown");
            group.set_message("server restarted while this group was running");
            group.set_cleanup_acknowledged(false);
            record->run.set_results_complete(false);
          }
        }
        interrupted = true;
      }
      for (auto &group : *record->run.mutable_groups()) {
        for (auto &receipt : *group.mutable_exports()) {
          if (receipt.state() != "intent")
            continue;
          try {
            if (std::filesystem::exists(receipt.path()) &&
                digest_file(receipt.path()) == receipt.digest())
              receipt.set_state("committed");
            else
              receipt.set_state("unknown");
          } catch (...) {
            receipt.set_state("unknown");
          }
          interrupted = true;
        }
      }
      records.emplace(record->run.run_id(), record);
      if (!record->run.manifest().request_id().empty())
        request_index.emplace(request_key(record->owner_hash,
                                          record->run.manifest().request_id()),
                              record->run.run_id());
      if (interrupted) {
        record->run.set_revision(record->run.revision() + 1);
        try {
          persist_locked(*record);
        } catch (...) {
          // The old durable state is still conservative: next startup will
          // classify it as interrupted again and will never replay it.
        }
      }
    }
  }

  Code validate_request(const StartBatchRequest &request,
                        std::vector<std::vector<int>> &groups,
                        std::string &message) const {
    if (request.request_id().empty() || request.request_id().size() > 256) {
      message = "request_id must contain 1..256 bytes";
      return Code::InvalidArgument;
    }
    if (request.body_source().empty() ||
        request.body_source().size() > 1024 * 1024 ||
        request.group_variable().empty()) {
      message = "batch body and group variable are required within limits";
      return Code::InvalidArgument;
    }
    try {
      (void)ctk::script::Engine{}.contains_batch(request.body_source());
    } catch (const ctk::script::Error &error) {
      message = error.what();
      return error.code;
    }
    if (request.inputs_size() > static_cast<int>(limits.max_inputs)) {
      message = "batch input manifest limit exceeded";
      return Code::ResourceExhausted;
    }
    for (const auto &input : request.inputs()) {
      if (input.file_path().empty() || !input.has_profile() ||
          !input.profile().frozen() || input.profile().profile_id().empty()) {
        message = "batch inputs require frozen compilation profiles";
        return Code::InvalidArgument;
      }
    }
    std::uint32_t group_count = 0;
    if (request.partition_case() == StartBatchRequest::kSize) {
      const auto size = request.size();
      if (!size || size > limits.max_group_size) {
        message = "batch size must be within the configured group limit";
        return Code::InvalidArgument;
      }
      group_count = static_cast<std::uint32_t>(
          (request.inputs_size() + static_cast<int>(size) - 1) / size);
      for (int i = 0; i < request.inputs_size(); i += static_cast<int>(size)) {
        std::vector<int> group;
        for (int j = i;
             j < std::min(request.inputs_size(), i + static_cast<int>(size));
             ++j)
          group.push_back(j);
        groups.push_back(std::move(group));
      }
    } else if (request.partition_case() == StartBatchRequest::kCount) {
      const auto count = request.count();
      if (count > limits.max_groups ||
          (request.inputs_size() > 0 && count > request.inputs_size()) ||
          (request.inputs_size() == 0 && count != 0)) {
        message = "batch count must not exceed input or group limits";
        return Code::InvalidArgument;
      }
      group_count = count;
      const auto base =
          count ? request.inputs_size() / static_cast<int>(count) : 0;
      const auto extra =
          count ? request.inputs_size() % static_cast<int>(count) : 0;
      if (base + (extra > 0 ? 1 : 0) >
          static_cast<int>(limits.max_group_size)) {
        message =
            "batch count creates a group larger than the configured limit";
        return Code::ResourceExhausted;
      }
      int offset = 0;
      for (std::uint32_t i = 0; i < count; ++i) {
        const auto length = base + (static_cast<int>(i) < extra ? 1 : 0);
        std::vector<int> group;
        for (int j = 0; j < length; ++j)
          group.push_back(offset++);
        groups.push_back(std::move(group));
      }
    } else {
      message = "batch partition size or count is required";
      return Code::InvalidArgument;
    }
    if (group_count > limits.max_groups) {
      message = "batch group limit exceeded";
      return Code::ResourceExhausted;
    }
    if (request.has_jobs() && request.jobs() == 0) {
      message = "batch jobs must be positive";
      return Code::InvalidArgument;
    }
    if (request.has_memory_bytes() &&
        (request.memory_bytes() == 0 ||
         request.memory_bytes() > limits.max_memory_bytes)) {
      message = "batch memory must be positive and within the server limit";
      return Code::InvalidArgument;
    }
    return Code::Ok;
  }

  ScriptValue group_value(const BatchGroup &group) const {
    ScriptValue value;
    auto *object = value.mutable_object();
    auto *index = (*object->mutable_fields())["index"].mutable_scalar();
    index->set_integer(group.index());
    auto *inputs = (*object->mutable_fields())["inputs"].mutable_files();
    for (const auto &input : group.inputs())
      *inputs->add_inputs() = input;
    auto *paths = (*object->mutable_fields())["paths"].mutable_list();
    for (const auto &input : group.inputs()) {
      auto *path = paths->add_values()->mutable_scalar();
      path->set_text(input.file_path());
    }
    return value;
  }

  Code run_group(const std::shared_ptr<Record> &record, int group_index,
                 std::string &message) {
    BatchGroup group;
    {
      std::lock_guard guard(mutex);
      if (journal_failed) {
        message = "durable batch journal is fail-closed until server restart";
        return Code::Internal;
      }
      group.CopyFrom(record->run.groups(group_index));
    }
    ctk::match::v1::OpenResourceScopeRequest scope_request;
    for (const auto &input : group.inputs())
      *scope_request.add_inputs() = input;
    scope_request.set_transient(true);
    scope_request.set_jobs(record->run.manifest().has_jobs()
                               ? record->run.manifest().jobs()
                               : limits.max_jobs);
    if (record->run.manifest().has_memory_bytes())
      scope_request.set_memory_bytes(record->run.manifest().memory_bytes());
    std::vector<ResourceInputReservation> reservations;
    for (const auto &input : group.inputs()) {
      (void)ctk::clang_layer::resolve_file_descriptor(input);
      const auto identity = ctk::application::input_identity(input);
      reservations.push_back(
          {identity, input.estimated_parse_bytes()
                         ? input.estimated_parse_bytes()
                         : std::max<std::uint64_t>(input.source_bytes(), 1)});
    }
    ctk::match::v1::ResourceScopeInfo scope;
    auto code = resources->open_scope(record->owner_hash, scope_request,
                                      reservations, scope, message);
    if (code != Code::Ok) {
      std::lock_guard guard(mutex);
      record->run.mutable_groups(group_index)->set_cleanup_acknowledged(true);
      return code;
    }

    {
      std::lock_guard guard(mutex);
      record->run.mutable_groups(group_index)
          ->set_resource_scope_id(scope.resource_scope_id());
      record->run.set_revision(record->run.revision() + 1);
      try {
        persist_locked(*record);
      } catch (const std::exception &error) {
        message = error.what();
        ctk::match::v1::ResourceScopeInfo released;
        (void)resources->release_scope(record->owner_hash,
                                       scope.resource_scope_id(), released);
        return Code::ResourceExhausted;
      }
    }

    ScriptRequest request;
    request.set_source(record->run.manifest().body_source());
    request.set_max_steps(10000);
    request.set_collect_final(true);
    request.set_resource_scope_id(scope.resource_scope_id());
    (*request
          .mutable_initial_values())[record->run.manifest().group_variable()] =
        group_value(group);
    auto cleanup_scope = [&]() {
      ctk::match::v1::ResourceScopeInfo released;
      const auto release_code = resources->release_scope(
          record->owner_hash, scope.resource_scope_id(), released);
      if (release_code == Code::Ok && released.cleanup_acknowledged()) {
        std::lock_guard guard(mutex);
        auto *target = record->run.mutable_groups(group_index);
        target->set_cleanup_acknowledged(true);
        record->run.set_peak_accounted_bytes(
            std::max(record->run.peak_accounted_bytes(),
                     released.peak_accounted_bytes()));
        record->run.set_peak_reserved_bytes(std::max(
            record->run.peak_reserved_bytes(), released.peak_reserved_bytes()));
      }
      return release_code == Code::Ok && released.cleanup_acknowledged();
    };
    ScopeExit ensure_cleanup([&] {
      try {
        (void)cleanup_scope();
      } catch (...) {
      }
    });
    if (record->cancel_requested.load()) {
      code = Code::Cancelled;
      message = "batch cancellation requested";
    } else {
      try {
        for (int i = 0; i < group.inputs_size(); ++i) {
          if (i >= group.source_revisions_size()) {
            code = Code::FailedPrecondition;
            message = "batch source revision manifest is incomplete";
            break;
          }
          const auto &saved = group.source_revisions(i);
          if (saved.starts_with("main:") &&
              digest_file(input_path(group.inputs(i))) != saved.substr(5)) {
            code = Code::FailedPrecondition;
            message = "batch main source changed since the manifest was frozen";
            break;
          }
        }
        if (code == Code::Ok) {
          const std::vector<ctk::match::v1::InputDescriptor> inputs(
              group.inputs().begin(), group.inputs().end());
          const auto current = scripts.capture_source_revisions(
              inputs, record->owner_hash, scope.resource_scope_id());
          for (int i = 0; i < group.inputs_size(); ++i) {
            const auto current_revision =
                "closure:" +
                closure_revision(group.inputs(i).profile().profile_id(),
                                 current[i]);
            const auto &saved = group.source_revisions(i);
            if (saved.starts_with("closure:") && saved != current_revision) {
              code = Code::FailedPrecondition;
              message = "batch source dependency closure changed since the "
                        "manifest was frozen";
              break;
            }
          }
          if (code == Code::Ok) {
            std::lock_guard guard(mutex);
            auto *target = record->run.mutable_groups(group_index);
            for (int i = 0; i < target->inputs_size(); ++i) {
              target->set_source_revisions(
                  i, "closure:" + closure_revision(
                                      target->inputs(i).profile().profile_id(),
                                      current[i]));
            }
            record->run.set_revision(record->run.revision() + 1);
            try {
              persist_locked(*record);
            } catch (const std::exception &error) {
              code = Code::ResourceExhausted;
              message = error.what();
            }
          }
        }
      } catch (const std::exception &error) {
        code = Code::FailedPrecondition;
        message = error.what();
      }
    }
    if (code == Code::Ok) {
      try {
        auto result = scripts.run(
            request, [record] { return !record->cancel_requested.load(); },
            record->owner_hash,
            [this, record, group_index](const std::string &export_path,
                                        const ScriptValue &value,
                                        const std::string &format) {
              return export_value(record, group_index, export_path, value,
                                  format);
            });
        code = result.code;
        message = result.message;
        if (code == Code::Ok) {
          std::lock_guard guard(mutex);
          std::uint64_t retained_bytes = result.response.ByteSizeLong();
          std::uint64_t retained_items = response_item_count(result.response);
          for (int i = 0; i < record->run.groups_size(); ++i) {
            if (i == group_index || !record->run.groups(i).has_result())
              continue;
            retained_bytes += record->run.groups(i).result().ByteSizeLong();
            retained_items +=
                response_item_count(record->run.groups(i).result());
          }
          if (retained_bytes > limits.max_result_bytes ||
              retained_items > limits.max_result_items) {
            code = Code::ResourceExhausted;
            message = "durable batch detached result limit exceeded";
          } else {
            auto *target = record->run.mutable_groups(group_index);
            target->mutable_result()->Swap(&result.response);
          }
        }
      } catch (const std::exception &error) {
        code = Code::Internal;
        message = error.what();
      } catch (...) {
        code = Code::Internal;
        message = "durable batch script execution threw an unknown exception";
      }
    }
    const bool cleanup_acknowledged = cleanup_scope();
    ensure_cleanup.dismiss();
    if (!cleanup_acknowledged) {
      code = Code::Aborted;
      message = "batch resource cleanup could not be acknowledged";
    }
    return code;
  }

  std::pair<Code, std::string>
  export_value(const std::shared_ptr<Record> &record, int group_index,
               const std::string &requested_path, const ScriptValue &value,
               const std::string &format) {
    if (requested_path.empty())
      return {Code::InvalidArgument, "batch export path is empty"};
    std::string payload;
    if (format == "proto" || format == "protobuf") {
      if (!value.SerializeToString(&payload))
        return {Code::Internal, "could not serialize batch export"};
    } else if (format == "json") {
      google::protobuf::util::JsonPrintOptions options;
      options.preserve_proto_field_names = true;
      auto status =
          google::protobuf::util::MessageToJsonString(value, &payload, options);
      if (!status.ok())
        return {Code::InvalidArgument, status.ToString()};
    } else {
      return {Code::InvalidArgument,
              "batch export format must be json or proto"};
    }
    const auto digest = sha256(payload);
    std::filesystem::path target(requested_path);
    if (!target.is_absolute())
      target = std::filesystem::absolute(target);
    std::error_code canonical_error;
    auto canonical_target =
        std::filesystem::weakly_canonical(target, canonical_error);
    target = canonical_error ? target.lexically_normal() : canonical_target;
    const auto target_string = target.string();
    std::error_code destination_error;
    if (std::filesystem::is_directory(target, destination_error) &&
        !destination_error)
      return {Code::InvalidArgument,
              "batch export destination is an existing directory"};
    {
      std::lock_guard guard(mutex);
      auto *group = record->run.mutable_groups(group_index);
      for (int group_number = 0; group_number < record->run.groups_size();
           ++group_number) {
        const auto &receipt_group = record->run.groups(group_number);
        for (const auto &receipt : receipt_group.exports()) {
          if (receipt.path() != target_string)
            continue;
          if (group_number == group_index && receipt.state() == "committed" &&
              receipt.digest() == digest) {
            try {
              if (std::filesystem::exists(target) &&
                  digest_file(target) == receipt.digest())
                return {Code::Ok, {}};
            } catch (...) {
            }
            return {Code::FailedPrecondition,
                    "committed batch export no longer matches its receipt"};
          }
          return {
              Code::FailedPrecondition,
              "batch export path is already owned by another committed intent"};
        }
      }
      /* The path is reserved by a durable intent before the write. */
      auto *intent = group->add_exports();
      intent->set_path(target_string);
      intent->set_digest(digest);
      intent->set_state("intent");
      record->run.set_revision(record->run.revision() + 1);
      try {
        persist_locked(*record);
      } catch (const std::exception &error) {
        intent->set_state("unknown");
        record->run.set_revision(record->run.revision() + 1);
        try {
          persist_locked(*record);
        } catch (...) {
        }
        return {Code::Aborted, error.what()};
      }
    }
    try {
      ctk::platform::durable_atomic_write(target, payload);
    } catch (const std::exception &error) {
      std::lock_guard guard(mutex);
      auto *receipt =
          record->run.mutable_groups(group_index)
              ->mutable_exports()
              ->Mutable(record->run.groups(group_index).exports_size() - 1);
      receipt->set_state("unknown");
      record->run.set_revision(record->run.revision() + 1);
      try {
        persist_locked(*record);
      } catch (...) {
      }
      return {Code::Internal, error.what()};
    }
    {
      std::lock_guard guard(mutex);
      auto *exports =
          record->run.mutable_groups(group_index)->mutable_exports();
      auto *receipt = exports->Mutable(exports->size() - 1);
      receipt->set_state("committed");
      record->run.set_revision(record->run.revision() + 1);
      try {
        persist_locked(*record);
      } catch (const std::exception &error) {
        receipt->set_state("unknown");
        record->run.set_revision(record->run.revision() + 1);
        try {
          persist_locked(*record);
        } catch (...) {
        }
        return {Code::Aborted, error.what()};
      }
    }
    return {Code::Ok, {}};
  }

  void finish_group(const std::shared_ptr<Record> &record, int index, Code code,
                    const std::string &message) {
    std::lock_guard guard(mutex);
    auto *group = record->run.mutable_groups(index);
    if (code != Code::Ok)
      group->clear_result();
    if (code == Code::Ok) {
      group->set_state("completed");
      group->clear_message();
    } else if (code == Code::Cancelled || record->cancel_requested.load()) {
      group->set_state("cancelled");
      group->set_message(message.empty() ? "batch cancelled" : message);
      record->run.set_results_complete(false);
    } else if (code == Code::Aborted) {
      group->set_state("unknown");
      group->set_message(message);
      record->run.set_results_complete(false);
    } else {
      group->set_state("failed");
      group->set_message(message);
      record->run.set_results_complete(false);
    }
    record->run.set_revision(record->run.revision() + 1);
    if (!group->cleanup_acknowledged() && group->state() != "unknown") {
      group->set_state("unknown");
      group->set_message("native resource cleanup is unconfirmed");
      record->run.set_results_complete(false);
    }
    try {
      persist_locked(*record);
    } catch (...) {
      record->run.set_state("interrupted");
    }
  }

  void run_record(const std::shared_ptr<Record> &record) {
    {
      std::lock_guard guard(mutex);
      if (journal_failed)
        return;
      if (record->run.state() != "queued")
        return;
      record->run.set_state("running");
      record->run.set_revision(record->run.revision() + 1);
      try {
        persist_locked(*record);
      } catch (...) {
        record->run.set_state("interrupted");
        return;
      }
    }
    for (int index = 0; index < record->run.groups_size(); ++index) {
      {
        std::lock_guard guard(mutex);
        if (journal_failed)
          break;
        if (record->cancel_requested.load()) {
          break;
        }
        if (record->run.groups(index).state() != "pending")
          continue;
        auto *group = record->run.mutable_groups(index);
        group->set_state("running");
        record->run.set_revision(record->run.revision() + 1);
        try {
          persist_locked(*record);
        } catch (...) {
          group->set_state("pending");
          record->run.set_state("interrupted");
          return;
        }
      }
      std::string message;
      Code code = Code::Internal;
      try {
        code = run_group(record, index, message);
      } catch (const std::exception &error) {
        message = error.what();
      } catch (...) {
        message = "durable batch group execution failed";
      }
      finish_group(record, index, code, message);
      if (code != Code::Ok && !record->run.manifest().continue_on_error()) {
        std::lock_guard guard(mutex);
        for (int skipped = index + 1; skipped < record->run.groups_size();
             ++skipped) {
          auto *group = record->run.mutable_groups(skipped);
          if (group->state() == "pending") {
            group->set_state("pending");
            group->set_message("not started after earlier group failure");
          }
        }
        break;
      }
    }
    std::lock_guard guard(mutex);
    if (journal_failed)
      return;
    bool has_unknown = false;
    bool has_failed = false;
    bool has_pending = false;
    bool has_cancelled = false;
    bool all_completed = true;
    for (const auto &group : record->run.groups()) {
      has_unknown |= group.state() == "unknown";
      has_failed |= group.state() == "failed";
      has_pending |= group.state() == "pending";
      has_cancelled |= group.state() == "cancelled";
      all_completed &= group.state() == "completed";
    }
    record->run.set_results_complete(all_completed);
    if (has_unknown)
      record->run.set_state("interrupted");
    else if (has_cancelled || record->cancel_requested.load())
      record->run.set_state("cancelled");
    else if (has_pending)
      record->run.set_state("interrupted");
    else if (has_failed)
      record->run.set_state("failed");
    else
      record->run.set_state("completed");
    record->run.set_revision(record->run.revision() + 1);
    try {
      persist_locked(*record);
    } catch (...) {
      record->run.set_state("interrupted");
    }
  }

  void work_loop() {
    for (;;) {
      std::shared_ptr<Record> record;
      {
        std::unique_lock lock(mutex);
        changed.wait(lock, [&] { return stopping || !queue.empty(); });
        if (stopping && queue.empty())
          return;
        const auto id = std::move(queue.front());
        queue.pop();
        if (auto found = records.find(id); found != records.end())
          record = found->second;
      }
      if (record)
        run_record(record);
    }
  }

  Code start(const StartBatchRequest &request, const std::string &owner,
             BatchRun &response, std::string &message) {
    {
      std::lock_guard guard(mutex);
      const auto healthy = ensure_journal_healthy_locked(message);
      if (healthy != Code::Ok)
        return healthy;
    }
    std::vector<std::vector<int>> groups;
    auto code = validate_request(request, groups, message);
    if (code != Code::Ok)
      return code;
    const auto owner_hash = owner_key(owner);
    const auto key = request_key(owner_hash, request.request_id());
    {
      std::lock_guard guard(mutex);
      const auto healthy = ensure_journal_healthy_locked(message);
      if (healthy != Code::Ok)
        return healthy;
      if (const auto existing = request_index.find(key);
          existing != request_index.end()) {
        const auto record = records.at(existing->second);
        if (!google::protobuf::util::MessageDifferencer::Equals(
                record->run.manifest(), request)) {
          message =
              "request_id was already used with a different batch payload";
          return Code::FailedPrecondition;
        }
        copy_response(*record, response);
        return Code::Ok;
      }
      if (records.size() >= limits.max_manifests ||
          active_runs_locked() >= limits.max_active_runs) {
        message = "durable batch admission limit exceeded";
        return Code::ResourceExhausted;
      }
      if (stopping) {
        message = "durable batch registry is shutting down";
        return Code::Cancelled;
      }
    }
    std::lock_guard guard(mutex);
    const auto healthy = ensure_journal_healthy_locked(message);
    if (healthy != Code::Ok)
      return healthy;
    if (const auto existing = request_index.find(key);
        existing != request_index.end()) {
      const auto record = records.at(existing->second);
      if (!google::protobuf::util::MessageDifferencer::Equals(
              record->run.manifest(), request)) {
        message = "request_id was already used with a different batch payload";
        return Code::FailedPrecondition;
      }
      copy_response(*record, response);
      return Code::Ok;
    }
    if (records.size() >= limits.max_manifests ||
        active_runs_locked() >= limits.max_active_runs) {
      message = "durable batch admission limit exceeded";
      return Code::ResourceExhausted;
    }
    if (stopping) {
      message = "durable batch registry is shutting down";
      return Code::Cancelled;
    }
    auto record = std::make_shared<Record>();
    record->owner_hash = owner_hash;
    record->path = owner_directory(owner_hash) / (random_id() + ".pb");
    auto &run = record->run;
    run.set_run_id(record->path.stem().string());
    run.set_revision(1);
    run.set_state("queued");
    run.set_results_complete(groups.empty());
    *run.mutable_manifest() = request;
    for (const auto &indices : groups) {
      auto *group = run.add_groups();
      group->set_index(run.groups_size());
      group->set_state("pending");
      for (const auto index : indices) {
        const auto &input = request.inputs(index);
        *group->add_inputs() = input;
        try {
          group->add_source_revisions("main:" + digest_file(input_path(input)));
        } catch (const std::exception &error) {
          message = error.what();
          return Code::FailedPrecondition;
        }
      }
    }
    try {
      persist_locked(*record);
    } catch (const std::length_error &error) {
      message = error.what();
      return Code::ResourceExhausted;
    } catch (const std::exception &error) {
      message = error.what();
      return Code::Internal;
    }
    records.emplace(run.run_id(), record);
    request_index.emplace(key, run.run_id());
    queue_locked(record);
    copy_response(*record, response);
    return Code::Ok;
  }

  Code status(const BatchRunRequest &request, const std::string &owner,
              BatchRun &response, std::string &message) const {
    std::lock_guard guard(mutex);
    const auto healthy = ensure_journal_healthy_locked(message);
    if (healthy != Code::Ok)
      return healthy;
    std::shared_ptr<Record> record;
    const auto code = lookup_locked(request.run_id(), owner, record, message);
    if (code == Code::Ok)
      copy_response(*record, response);
    return code;
  }

  Code control(const BatchControlRequest &request, const std::string &owner,
               BatchRun &response, std::string &message, const char *action) {
    std::unique_lock guard(mutex);
    const auto healthy = ensure_journal_healthy_locked(message);
    if (healthy != Code::Ok)
      return healthy;
    if (stopping) {
      message = "durable batch registry is shutting down";
      return Code::Cancelled;
    }
    std::shared_ptr<Record> record;
    auto code = lookup_locked(request.run_id(), owner, record, message);
    if (code != Code::Ok)
      return code;
    const auto &run = record->run;
    if (request.expected_revision() != run.revision()) {
      message = "batch revision conflict";
      return Code::Aborted;
    }
    if (std::string_view(action) == "cancel") {
      if (run.state() != "queued" && run.state() != "running") {
        message = "only queued or running batches can be cancelled";
        return Code::FailedPrecondition;
      }
      BatchRun candidate;
      candidate.CopyFrom(run);
      candidate.set_revision(candidate.revision() + 1);
      try {
        persist_run_locked(*record, candidate);
      } catch (const std::exception &error) {
        message = error.what();
        return Code::Internal;
      }
      record->run.Swap(&candidate);
      record->cancel_requested.store(true);
    } else if (std::string_view(action) == "resume") {
      bool pending = false;
      for (const auto &group : run.groups()) {
        if (group.state() == "unknown") {
          message = "unknown group outcomes must be reconciled before resume";
          return Code::FailedPrecondition;
        }
        pending |= group.state() == "pending";
      }
      if (!pending || (run.state() != "interrupted" &&
                       run.state() != "failed" && run.state() != "cancelled")) {
        message = "batch has no resumable pending groups";
        return Code::FailedPrecondition;
      }
      if (active_runs_locked() >= limits.max_active_runs) {
        message = "durable batch active-run limit exceeded";
        return Code::ResourceExhausted;
      }
      BatchRun candidate;
      candidate.CopyFrom(run);
      candidate.set_state("queued");
      candidate.set_revision(candidate.revision() + 1);
      try {
        persist_run_locked(*record, candidate);
      } catch (const std::exception &error) {
        message = error.what();
        return Code::Internal;
      }
      record->run.Swap(&candidate);
      record->cancel_requested.store(false);
      queue_locked(record);
    } else {
      BatchRun candidate;
      candidate.CopyFrom(run);
      std::vector<int> retry_groups;
      for (int group_index = 0; group_index < candidate.groups_size();
           ++group_index) {
        auto &group = *candidate.mutable_groups(group_index);
        if (group.state() != "failed" && group.state() != "cancelled")
          continue;
        if (!group.cleanup_acknowledged()) {
          message = "failed group cleanup is unconfirmed";
          return Code::FailedPrecondition;
        }
        retry_groups.push_back(group_index);
      }
      if (retry_groups.empty() || run.state() == "queued" ||
          run.state() == "running") {
        message = "batch has no retryable failed or cancelled groups";
        return Code::FailedPrecondition;
      }
      if (active_runs_locked() >= limits.max_active_runs) {
        message = "durable batch active-run limit exceeded";
        return Code::ResourceExhausted;
      }
      const auto owner_hash = record->owner_hash;
      const auto expected_revision = run.revision();
      const auto manifest = run.manifest();
      guard.unlock();
      for (const auto group_index : retry_groups) {
        auto *group = candidate.mutable_groups(group_index);
        if (group->source_revisions_size() != group->inputs_size()) {
          message = "retry requires a complete frozen source revision";
          return Code::FailedPrecondition;
        }
        for (int i = 0; i < group->inputs_size(); ++i) {
          if (!group->inputs(i).profile().frozen() ||
              !group->source_revisions(i).starts_with("closure:")) {
            message = "retry requires a captured dependency closure";
            return Code::FailedPrecondition;
          }
        }
        ctk::match::v1::OpenResourceScopeRequest validation_request;
        for (const auto &input : group->inputs())
          *validation_request.add_inputs() = input;
        validation_request.set_transient(true);
        validation_request.set_jobs(manifest.has_jobs() ? manifest.jobs()
                                                        : limits.max_jobs);
        if (manifest.has_memory_bytes())
          validation_request.set_memory_bytes(manifest.memory_bytes());
        std::vector<ResourceInputReservation> reservations;
        try {
          for (const auto &input : group->inputs()) {
            (void)ctk::clang_layer::resolve_file_descriptor(input);
            const auto identity = ctk::application::input_identity(input);
            reservations.push_back(
                {identity,
                 input.estimated_parse_bytes()
                     ? input.estimated_parse_bytes()
                     : std::max<std::uint64_t>(input.source_bytes(), 1)});
          }
        } catch (const std::exception &error) {
          message = error.what();
          return Code::FailedPrecondition;
        }
        ctk::match::v1::ResourceScopeInfo validation_scope;
        code = resources->open_scope(owner_hash, validation_request,
                                     reservations, validation_scope, message);
        if (code != Code::Ok)
          return code;
        bool valid = true;
        try {
          const std::vector<ctk::match::v1::InputDescriptor> inputs(
              group->inputs().begin(), group->inputs().end());
          const auto closures = scripts.capture_source_revisions(
              inputs, owner_hash, validation_scope.resource_scope_id());
          for (int i = 0; i < group->inputs_size(); ++i) {
            const auto actual =
                "closure:" +
                closure_revision(group->inputs(i).profile().profile_id(),
                                 closures[i]);
            if (actual != group->source_revisions(i)) {
              message = "retry source dependency closure changed";
              valid = false;
              break;
            }
          }
        } catch (const std::exception &error) {
          message = error.what();
          valid = false;
        }
        ctk::match::v1::ResourceScopeInfo validation_released;
        const auto validation_cleanup = resources->release_scope(
            owner_hash, validation_scope.resource_scope_id(),
            validation_released);
        if (validation_cleanup != Code::Ok ||
            !validation_released.cleanup_acknowledged()) {
          message = "retry source validation cleanup was not acknowledged";
          return Code::Aborted;
        }
        if (!valid)
          return Code::FailedPrecondition;
        for (auto &receipt : *group->mutable_exports()) {
          if (receipt.state() == "unknown" || receipt.state() == "intent") {
            try {
              const auto path = std::filesystem::path(receipt.path());
              if (!std::filesystem::exists(path) ||
                  digest_file(path) != receipt.digest()) {
                message = "export outcome is unknown and cannot be replayed";
                return Code::FailedPrecondition;
              }
              receipt.set_state("committed");
            } catch (const std::exception &error) {
              message = error.what();
              return Code::FailedPrecondition;
            }
          }
        }
        group->set_state("pending");
        group->clear_message();
      }
      guard.lock();
      const auto healthy = ensure_journal_healthy_locked(message);
      if (healthy != Code::Ok)
        return healthy;
      if (record->run.revision() != expected_revision) {
        message = "batch revision changed during retry validation";
        return Code::Aborted;
      }
      if (active_runs_locked() >= limits.max_active_runs) {
        message = "durable batch active-run limit exceeded";
        return Code::ResourceExhausted;
      }
      candidate.set_state("queued");
      candidate.set_results_complete(false);
      candidate.set_revision(candidate.revision() + 1);
      try {
        persist_run_locked(*record, candidate);
      } catch (const std::exception &error) {
        message = error.what();
        return Code::Internal;
      }
      record->run.Swap(&candidate);
      record->cancel_requested.store(false);
      queue_locked(record);
    }
    copy_response(*record, response);
    return Code::Ok;
  }

  void shutdown() {
    {
      std::lock_guard guard(mutex);
      if (stopping)
        return;
      stopping = true;
      for (auto &[id, record] : records) {
        (void)id;
        if (record->run.state() == "running" || record->run.state() == "queued")
          record->cancel_requested.store(true);
      }
    }
    changed.notify_all();
    if (worker.joinable())
      worker.join();
    std::lock_guard guard(mutex);
    for (auto &[id, record] : records) {
      (void)id;
      if (record->run.state() == "running" || record->run.state() == "queued") {
        record->run.set_state("interrupted");
        for (auto &group : *record->run.mutable_groups()) {
          if (group.state() == "running") {
            group.set_state("unknown");
            group.set_cleanup_acknowledged(false);
            group.set_message("server shut down before group completion");
          }
        }
        record->run.set_results_complete(false);
        record->run.set_revision(record->run.revision() + 1);
        try {
          persist_locked(*record);
        } catch (...) {
        }
      }
    }
  }
};

BatchRegistry::BatchRegistry(ScriptController &scripts,
                             std::shared_ptr<ResourceManager> resources,
                             std::filesystem::path storage_root,
                             BatchRegistryLimits limits)
    : impl_(std::make_unique<Impl>(scripts, std::move(resources),
                                   std::move(storage_root), limits)) {}
BatchRegistry::~BatchRegistry() { shutdown(); }
Code BatchRegistry::start(const StartBatchRequest &request,
                          const std::string &owner, BatchRun &response,
                          std::string &message) {
  return impl_->start(request, owner, response, message);
}
Code BatchRegistry::status(const BatchRunRequest &request,
                           const std::string &owner, BatchRun &response,
                           std::string &message) const {
  return impl_->status(request, owner, response, message);
}
Code BatchRegistry::cancel(const BatchControlRequest &request,
                           const std::string &owner, BatchRun &response,
                           std::string &message) {
  return impl_->control(request, owner, response, message, "cancel");
}
Code BatchRegistry::resume(const BatchControlRequest &request,
                           const std::string &owner, BatchRun &response,
                           std::string &message) {
  return impl_->control(request, owner, response, message, "resume");
}
Code BatchRegistry::retry(const BatchControlRequest &request,
                          const std::string &owner, BatchRun &response,
                          std::string &message) {
  return impl_->control(request, owner, response, message, "retry");
}
void BatchRegistry::shutdown() { impl_->shutdown(); }

} // namespace ctk::application
