#pragma once

#include "ctk/cache/cache_records.hpp"
#include "ctk/cache/compilation_context.hpp"

#include <stop_token>

namespace ctk::cache::detail {

// One caller's immutable identity and cancellation. This token never controls
// a shared load: cancelling a caller must not cancel the other flight waiters.
struct AcquisitionRequest {
  std::string path;
  std::string identity;
  std::string digest;
  const CompilationContext &context;
  std::stop_token cancellation;
  std::string transient_owner;

  void check_cancelled() const;
};

enum class AcquisitionKind { Candidate, Waiter, Builder };

// Strong handles copied under metadata locking. They remain valid while I/O
// runs unlocked; identity and reuse eligibility must be checked again
// afterward.
struct AcquisitionAttempt {
  std::shared_ptr<FileEntry> file;
  std::shared_ptr<ProfileEntry> profile;
  std::shared_ptr<SnapshotRecord> candidate;
  std::shared_ptr<Flight> flight;
  AcquisitionKind kind = AcquisitionKind::Builder;
  std::uint64_t epoch = 0;
  std::uint64_t generation = 0;
};

struct FlightResult {
  SnapshotPtr snapshot;
  std::uint64_t publication_epoch = 0;
  std::exception_ptr error;
};

// Allocate/copy everything practical before admission. Keeping this object in
// the unlocked caller also keeps native ownership alive if admission throws.
struct PreparedSnapshot {
  SnapshotPtr snapshot;
  std::shared_ptr<SnapshotRecord> record;
  std::vector<InputObservation> observations;
  std::vector<std::shared_ptr<FileEntry>> inputs;
};

} // namespace ctk::cache::detail
