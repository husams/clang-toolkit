#pragma once

#include "ctk/application/query.hpp"
#include "ctk/clang/tooling.hpp"

#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace ctk::application::detail {

std::string profile_key(const FileInput &input);

// Admission policy for the single retained analysis session shared by RPCs.
class SessionAdmissionPolicy final {
public:
  explicit SessionAdmissionPolicy(ControllerSettings settings);
  ~SessionAdmissionPolicy();
  SessionAdmissionPolicy(const SessionAdmissionPolicy &) = delete;
  SessionAdmissionPolicy &operator=(const SessionAdmissionPolicy &) = delete;

  std::vector<LimitViolation>
  reserve_batch(const std::vector<FileInput> &inputs,
                std::vector<std::pair<std::string, FileInput>> &claims);
  std::vector<LimitViolation>
  reserve_initial(const std::vector<FileInput> &inputs,
                  std::vector<std::pair<std::string, FileInput>> &claims);
  std::vector<LimitViolation> reserve_stream_overhead();
  void release_stream_overhead();
  void rollback(const std::vector<std::pair<std::string, FileInput>> &claims);
  void reconcile(const std::string &key, std::uint64_t actual, bool retained,
                 bool release_claim, bool evicted = false);
  void stop_admission();

private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};

// Shared analysis-session owner: engine snapshots and their admission ledger
// live beyond any individual query stream.
class AnalysisSession final {
public:
  AnalysisSession(ControllerSettings settings,
                  std::shared_ptr<ctk::clang_layer::IQueryEngine> engine);

  SessionAdmissionPolicy admission;
  std::shared_ptr<ctk::clang_layer::IQueryEngine> engine;

  std::shared_ptr<std::mutex> profile_mutex(const std::string &key);

private:
  std::mutex profile_mutex_map_mutex_;
  std::unordered_map<std::string, std::weak_ptr<std::mutex>> profile_mutexes_;
};

} // namespace ctk::application::detail
