#include "analysis_session.hpp"

#include <filesystem>
#include <limits>
#include <mutex>
#include <unordered_map>
#include <utility>

namespace ctk::application::detail {
namespace {
constexpr std::uint64_t kAstEstimateBytes = 16ULL * 1024 * 1024;
constexpr std::uint64_t kParseOverheadEstimateBytes = 16ULL * 1024 * 1024;
constexpr std::uint64_t kPerStreamOverheadBytes = 33ULL * 1024 * 1024;

std::string normalized_path(const FileInput &input) {
  std::filesystem::path path(input.path);
  if (path.is_relative())
    path = std::filesystem::path(input.working_directory) / path;
  return path.lexically_normal().string();
}

std::uint64_t saturated_add(std::uint64_t lhs, std::uint64_t rhs) {
  return rhs > std::numeric_limits<std::uint64_t>::max() - lhs
             ? std::numeric_limits<std::uint64_t>::max()
             : lhs + rhs;
}

LimitViolation stopped_violation() {
  return {"controller.admission", 0, 0, 1, 1};
}
} // namespace

std::string profile_key(const FileInput &input) {
  std::string key;
  const auto append = [&](const std::string &value) {
    key.append(std::to_string(value.size())).push_back(':');
    key.append(value);
  };
  append(normalized_path(input));
  append(input.working_directory);
  append(input.compilation_database);
  key.append(std::to_string(input.compile_arguments.size())).push_back(';');
  for (const auto &argument : input.compile_arguments)
    append(argument);
  return key;
}

struct SessionAdmissionPolicy::Impl {
  struct Accounting {
    std::uint64_t memory_bytes = kAstEstimateBytes;
    bool measured = false;
    bool retained = false;
    std::size_t claims = 0;
    std::size_t parsing_reservations = 0;
  };

  explicit Impl(ControllerSettings config) : settings(std::move(config)) {}

  ControllerSettings settings;
  std::mutex mutex;
  std::unordered_map<std::string, Accounting> accounting;
  std::uint64_t accounted_files = 0, memory_bytes = 0, overhead_bytes = 0;
  bool accepting = true;
};

SessionAdmissionPolicy::SessionAdmissionPolicy(ControllerSettings settings)
    : impl_(std::make_unique<Impl>(std::move(settings))) {}
SessionAdmissionPolicy::~SessionAdmissionPolicy() = default;

std::vector<LimitViolation> SessionAdmissionPolicy::reserve_batch(
    const std::vector<FileInput> &inputs,
    std::vector<std::pair<std::string, FileInput>> &claims) {
  std::lock_guard lock(impl_->mutex);
  if (!impl_->accepting)
    return {stopped_violation()};
  std::unordered_map<std::string, FileInput> unique;
  for (const auto &file : inputs)
    unique.try_emplace(profile_key(file), file);
  std::uint64_t file_delta = 0, memory_delta = 0, overhead_delta = 0;
  for (const auto &[key, file] : unique) {
    const auto found = impl_->accounting.find(key);
    claims.emplace_back(key, file);
    if (found == impl_->accounting.end()) {
      ++file_delta;
      memory_delta = saturated_add(memory_delta, kAstEstimateBytes);
    }
    overhead_delta = saturated_add(overhead_delta, kParseOverheadEstimateBytes);
  }
  const auto projected_files =
      saturated_add(impl_->accounted_files, file_delta);
  const auto projected_memory =
      saturated_add(impl_->memory_bytes, memory_delta);
  const auto projected_overhead =
      saturated_add(impl_->overhead_bytes, overhead_delta);
  std::vector<LimitViolation> violations;
  if (projected_files > impl_->settings.max_files) {
    violations.push_back({"session.max_files", impl_->accounted_files,
                          impl_->settings.max_files, file_delta,
                          projected_files});
  }
  if (projected_memory > impl_->settings.max_memory_bytes) {
    violations.push_back({"session.max_memory_bytes", impl_->memory_bytes,
                          impl_->settings.max_memory_bytes, memory_delta,
                          projected_memory});
  }
  if (projected_overhead > impl_->settings.overhead_memory_bytes) {
    violations.push_back({"session.overhead_memory_bytes",
                          impl_->overhead_bytes,
                          impl_->settings.overhead_memory_bytes, overhead_delta,
                          projected_overhead});
  }
  if (!violations.empty()) {
    claims.clear();
    return violations;
  }
  for (const auto &[key, _] : claims) {
    const auto found = impl_->accounting.try_emplace(key).first;
    ++found->second.claims;
    ++found->second.parsing_reservations;
  }
  impl_->accounted_files = projected_files;
  impl_->memory_bytes = projected_memory;
  impl_->overhead_bytes = projected_overhead;
  return {};
}

std::vector<LimitViolation> SessionAdmissionPolicy::reserve_initial(
    const std::vector<FileInput> &inputs,
    std::vector<std::pair<std::string, FileInput>> &claims) {
  std::lock_guard lock(impl_->mutex);
  if (!impl_->accepting)
    return {stopped_violation()};
  std::unordered_map<std::string, FileInput> unique;
  for (const auto &file : inputs)
    unique.try_emplace(profile_key(file), file);
  std::uint64_t file_delta = 0, memory_delta = 0, overhead_delta = 0;
  for (const auto &[key, file] : unique) {
    const auto found = impl_->accounting.find(key);
    claims.emplace_back(key, file);
    if (found == impl_->accounting.end()) {
      ++file_delta;
      memory_delta = saturated_add(memory_delta, kAstEstimateBytes);
    }
    overhead_delta = saturated_add(overhead_delta, kParseOverheadEstimateBytes);
  }
  const auto projected_files =
      saturated_add(impl_->accounted_files, file_delta);
  const auto projected_memory =
      saturated_add(impl_->memory_bytes, memory_delta);
  const auto requested_overhead =
      saturated_add(kPerStreamOverheadBytes, overhead_delta);
  const auto projected_overhead =
      saturated_add(impl_->overhead_bytes, requested_overhead);
  std::vector<LimitViolation> violations;
  if (projected_files > impl_->settings.max_files) {
    violations.push_back({"session.max_files", impl_->accounted_files,
                          impl_->settings.max_files, file_delta,
                          projected_files});
  }
  if (projected_memory > impl_->settings.max_memory_bytes) {
    violations.push_back({"session.max_memory_bytes", impl_->memory_bytes,
                          impl_->settings.max_memory_bytes, memory_delta,
                          projected_memory});
  }
  if (projected_overhead > impl_->settings.overhead_memory_bytes) {
    violations.push_back({"session.overhead_memory_bytes",
                          impl_->overhead_bytes,
                          impl_->settings.overhead_memory_bytes,
                          requested_overhead, projected_overhead});
  }
  if (!violations.empty()) {
    claims.clear();
    return violations;
  }
  for (const auto &[key, _] : claims) {
    const auto found = impl_->accounting.try_emplace(key).first;
    ++found->second.claims;
    ++found->second.parsing_reservations;
  }
  impl_->accounted_files = projected_files;
  impl_->memory_bytes = projected_memory;
  impl_->overhead_bytes = projected_overhead;
  return {};
}

std::vector<LimitViolation> SessionAdmissionPolicy::reserve_stream_overhead() {
  std::lock_guard lock(impl_->mutex);
  if (!impl_->accepting)
    return {stopped_violation()};
  const auto projected =
      saturated_add(impl_->overhead_bytes, kPerStreamOverheadBytes);
  if (projected <= impl_->settings.overhead_memory_bytes) {
    impl_->overhead_bytes = projected;
    return {};
  }
  return {{"session.overhead_memory_bytes", impl_->overhead_bytes,
           impl_->settings.overhead_memory_bytes, kPerStreamOverheadBytes,
           projected}};
}

void SessionAdmissionPolicy::release_stream_overhead() {
  std::lock_guard lock(impl_->mutex);
  impl_->overhead_bytes -=
      std::min(impl_->overhead_bytes, kPerStreamOverheadBytes);
}

void SessionAdmissionPolicy::rollback(
    const std::vector<std::pair<std::string, FileInput>> &claims) {
  std::lock_guard lock(impl_->mutex);
  for (const auto &[key, _] : claims) {
    const auto found = impl_->accounting.find(key);
    if (found == impl_->accounting.end())
      continue;
    if (found->second.claims > 0)
      --found->second.claims;
    if (found->second.parsing_reservations > 0) {
      --found->second.parsing_reservations;
      impl_->overhead_bytes -=
          std::min(impl_->overhead_bytes, kParseOverheadEstimateBytes);
    }
    if (found->second.retained || found->second.claims != 0)
      continue;
    impl_->memory_bytes -= found->second.memory_bytes;
    impl_->accounting.erase(found);
    if (impl_->accounted_files > 0)
      --impl_->accounted_files;
  }
}

void SessionAdmissionPolicy::reconcile(const std::string &key,
                                       std::uint64_t actual, bool retained,
                                       bool release_claim, bool evicted) {
  std::lock_guard lock(impl_->mutex);
  auto found = impl_->accounting.find(key);
  if (found == impl_->accounting.end())
    return;
  if (release_claim) {
    if (found->second.claims > 0)
      --found->second.claims;
    if (found->second.parsing_reservations > 0) {
      --found->second.parsing_reservations;
      impl_->overhead_bytes -=
          std::min(impl_->overhead_bytes, kParseOverheadEstimateBytes);
    }
  }
  if (retained) {
    found->second.retained = true;
    found->second.measured = true;
    impl_->memory_bytes -= found->second.memory_bytes;
    impl_->memory_bytes = saturated_add(impl_->memory_bytes, actual);
    found->second.memory_bytes = actual;
  } else if (evicted && found->second.retained) {
    impl_->memory_bytes -= found->second.memory_bytes;
    found->second.retained = false;
    found->second.measured = false;
    found->second.memory_bytes =
        found->second.claims > 0 ? kAstEstimateBytes : 0;
    impl_->memory_bytes =
        saturated_add(impl_->memory_bytes, found->second.memory_bytes);
    if (found->second.claims == 0) {
      impl_->accounting.erase(found);
      if (impl_->accounted_files > 0)
        --impl_->accounted_files;
    }
  } else if (!found->second.retained && found->second.claims == 0) {
    impl_->memory_bytes -= found->second.memory_bytes;
    impl_->accounting.erase(found);
    if (impl_->accounted_files > 0)
      --impl_->accounted_files;
  }
}

void SessionAdmissionPolicy::stop_admission() {
  std::lock_guard lock(impl_->mutex);
  impl_->accepting = false;
}

AnalysisSession::AnalysisSession(
    ControllerSettings settings,
    std::shared_ptr<ctk::clang_layer::IQueryEngine> matcher)
    : admission(settings), engine(std::move(matcher)) {
#if defined(CTK_WITH_CLANG)
  if (!engine)
    engine = ctk::clang_layer::make_query_engine();
#endif
}

std::shared_ptr<std::mutex>
AnalysisSession::profile_mutex(const std::string &key) {
  std::lock_guard lock(profile_mutex_map_mutex_);
  std::erase_if(profile_mutexes_,
                [](const auto &entry) { return entry.second.expired(); });
  auto &weak = profile_mutexes_[key];
  auto mutex = weak.lock();
  if (!mutex) {
    mutex = std::make_shared<std::mutex>();
    weak = mutex;
  }
  return mutex;
}

} // namespace ctk::application::detail
