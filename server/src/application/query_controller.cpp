#include "ctk/application/query.hpp"

#include "analysis_session.hpp"
#include "ctk/clang/tooling.hpp"
#include "query_executor.hpp"

#include <algorithm>
#include <filesystem>
#include <future>
#include <limits>
#include <optional>
#include <queue>
#include <thread>
#include <unordered_map>
#include <unordered_set>
#include <utility>

namespace ctk::application {
namespace {
std::string normalize_path(const FileInput &input) {
  std::filesystem::path path(input.path);
  if (path.is_relative()) {
    path = std::filesystem::path(input.working_directory) / path;
  }
  return path.lexically_normal().string();
}

std::string profile_key(const FileInput &input) {
  return detail::profile_key(input);
}

ControllerSettings normalized_settings(ControllerSettings settings) {
  if (settings.workers == 0)
    settings.workers = 1;
  if (settings.pending_requests == 0)
    settings.pending_requests = 1;
  return settings;
}

QueryEvent event(EventKind kind, const std::string &request_id) {
  QueryEvent result{};
  result.kind = kind;
  result.request_id = request_id;
  return result;
}

} // namespace

struct QueryController::Impl {
  struct Session {
    explicit Session(std::shared_ptr<IQueryEventSink> event_sink)
        : sink(std::move(event_sink)) {}
    std::mutex mutex;
    std::shared_ptr<IQueryEventSink> sink;
    std::string query;
    bool query_defined = false;
    bool matching = false;
    bool input_closed = false;
    bool terminal = false;
    bool initial_request = false;
    bool call_reservation_active = false;
    bool call_reservation_released = false;
    Outcome terminal_outcome;
    std::uint64_t accepted_files = 0;
    std::uint64_t completed_files = 0;
    std::uint64_t match_count = 0;
    std::size_t in_flight = 0;
    std::vector<std::pair<std::string, FileInput>> files;
    std::vector<std::pair<std::string, FileInput>> fresh_profiles;
    std::unordered_set<std::string> claimed_profiles;
    std::unordered_map<std::string, bool> scheduled;
    CancellationSource cancellation;
  };

  explicit Impl(ControllerSettings requested,
                std::shared_ptr<ctk::clang_layer::IQueryEngine> query_engine)
      : settings(normalized_settings(std::move(requested))),
        executor(settings.workers, settings.pending_requests),
        analysis(settings, std::move(query_engine)) {
    control_worker = std::thread([this] { control_loop(); });
  }

  ~Impl() { shutdown(); }

  void register_session(const std::shared_ptr<Session> &session) {
    std::lock_guard lock(sessions_mutex);
    std::erase_if(sessions, [](const auto &weak) { return weak.expired(); });
    sessions.emplace_back(session);
  }

  std::vector<std::shared_ptr<Session>> live_sessions() {
    std::vector<std::shared_ptr<Session>> active;
    std::lock_guard lock(sessions_mutex);
    std::erase_if(sessions, [](const auto &weak) { return weak.expired(); });
    active.reserve(sessions.size());
    for (const auto &weak : sessions) {
      if (auto session = weak.lock())
        active.push_back(std::move(session));
    }
    return active;
  }

  void shutdown() {
    if (shutdown_started.exchange(true))
      return;
    stop_admission();
    std::vector<std::shared_ptr<Session>> active;
    {
      std::lock_guard lock(sessions_mutex);
      for (const auto &weak : sessions) {
        if (auto session = weak.lock())
          active.push_back(std::move(session));
      }
      sessions.clear();
    }
    for (const auto &session : active)
      session->cancellation.cancel();
    {
      std::lock_guard lock(control_mutex);
      control_stopping = true;
    }
    control_cv.notify_all();
    if (control_worker.joinable() &&
        control_worker.get_id() != std::this_thread::get_id())
      control_worker.join();
    executor.shutdown();
  }

  bool enqueue(std::function<void()> task) {
    return executor.enqueue(std::move(task));
  }

  std::size_t pending_count() { return executor.pending_count(); }

  bool enqueue_control(std::function<void()> task) {
    std::lock_guard lock(control_mutex);
    if (control_stopping)
      return false;
    control_tasks.push(std::move(task));
    control_cv.notify_one();
    return true;
  }

  void control_loop() {
    for (;;) {
      std::function<void()> task;
      {
        std::unique_lock lock(control_mutex);
        control_cv.wait(
            lock, [&] { return control_stopping || !control_tasks.empty(); });
        if (control_stopping && control_tasks.empty())
          return;
        task = std::move(control_tasks.front());
        control_tasks.pop();
      }
      try {
        task();
      } catch (...) {
        // A rejected control command must not stop later commands from
        // draining.
      }
    }
  }

  void stop_admission() {
    analysis.admission.stop_admission();
    if (control_worker.get_id() == std::this_thread::get_id()) {
      if (!enqueue_control([this] { executor.stop_admission(); }))
        executor.stop_admission();
      return;
    }
    auto drained = std::make_shared<std::promise<void>>();
    auto ready = drained->get_future();
    if (enqueue_control([this, drained] {
          executor.stop_admission();
          drained->set_value();
        }))
      ready.wait();
    else
      executor.stop_admission();
  }

  void release_call(const std::shared_ptr<Session> &session) {
    {
      std::lock_guard lock(session->mutex);
      if (!session->call_reservation_active ||
          session->call_reservation_released)
        return;
      session->call_reservation_released = true;
    }
    analysis.admission.release_stream_overhead();
  }

  ControllerSettings settings;
  detail::QueryExecutor executor;
  detail::AnalysisSession analysis;
  std::mutex sessions_mutex;
  std::vector<std::weak_ptr<Session>> sessions;
  std::atomic<bool> shutdown_started{false};
  std::mutex control_mutex;
  std::condition_variable control_cv;
  std::queue<std::function<void()>> control_tasks;
  std::thread control_worker;
  bool control_stopping = false;
};

namespace {
class QueryHandle final : public IQueryHandle {
public:
  QueryHandle(std::shared_ptr<QueryController::Impl> impl,
              std::shared_ptr<QueryController::Impl::Session> session,
              bool owns_call = true)
      : impl_(std::move(impl)), session_(std::move(session)),
        owns_call_(owns_call) {}
  ~QueryHandle() override {
    if (owns_call_)
      transport_done();
  }
  void submit(QueryCommand command, std::function<void()> on_consumed) override;
  void close_input() override;
  void cancel() override;
  void reject(std::string request_id, Outcome outcome,
              std::function<void()> on_consumed) override;
  void transport_done() override;
  void schedule(std::vector<std::pair<std::string, FileInput>> files,
                std::vector<std::pair<std::string, FileInput>> rollback_files,
                const std::string &request_id);
  void process_command(QueryCommand command);

private:
  void finish_if_ready(const std::string &request_id = {});
  std::shared_ptr<QueryController::Impl> impl_;
  std::shared_ptr<QueryController::Impl::Session> session_;
  bool owns_call_;
};
} // namespace

namespace {
std::uint64_t
accepted_count(const std::shared_ptr<QueryController::Impl::Session> &session);
void publish_control(
    const std::shared_ptr<QueryController::Impl::Session> &session,
    const std::string &request_id, const std::string &action);
void release_pending_claims(
    QueryController::Impl *impl,
    const std::shared_ptr<QueryController::Impl::Session> &session);
} // namespace

QueryController::QueryController(ControllerSettings settings)
    : QueryController(std::move(settings), nullptr) {}

QueryController::QueryController(
    ControllerSettings settings,
    std::shared_ptr<ctk::clang_layer::IQueryEngine> engine)
    : impl_(std::make_shared<Impl>(std::move(settings), std::move(engine))) {}

QueryController::~QueryController() {
  if (impl_)
    impl_->shutdown();
}

std::shared_ptr<IQueryHandle>
QueryController::start(QueryRequest request,
                       std::shared_ptr<IQueryEventSink> sink) {
  auto session = std::make_shared<Impl::Session>(std::move(sink));
  impl_->register_session(session);
  session->initial_request = true;
  auto handle = std::make_shared<QueryHandle>(impl_, session);
  if (request.query.empty()) {
    Outcome outcome{
        OutcomeCode::InvalidArgument, "query expression must not be empty", {}};
    {
      std::lock_guard lock(session->mutex);
      session->terminal = true;
      session->terminal_outcome = outcome;
    }
    impl_->enqueue_control([session, outcome] {
      auto rejected = event(EventKind::Rejected, "start");
      rejected.outcome = outcome;
      session->sink->publish(std::move(rejected));
      auto complete = event(EventKind::Completed, "start");
      complete.outcome = outcome;
      session->sink->publish(std::move(complete));
      session->sink->on_complete(outcome);
    });
    return handle;
  }
  std::vector<FileInput> normalized_files;
  std::unordered_map<std::string, FileInput> unique_files;
  for (auto file : request.files) {
    file.path = normalize_path(file);
    unique_files.try_emplace(profile_key(file), std::move(file));
  }
  for (const auto &[_, file] : unique_files)
    normalized_files.push_back(file);
  std::vector<std::pair<std::string, FileInput>> claims;
  const auto violations =
      impl_->analysis.admission.reserve_initial(normalized_files, claims);
  if (!violations.empty()) {
    Outcome outcome{OutcomeCode::ResourceExhausted,
                    "file batch exceeds session limits", violations};
    {
      std::lock_guard lock(session->mutex);
      session->terminal = true;
      session->terminal_outcome = outcome;
    }
    impl_->enqueue_control([session, outcome] {
      auto rejected = event(EventKind::Rejected, "start");
      rejected.outcome = outcome;
      session->sink->publish(std::move(rejected));
      auto complete = event(EventKind::Completed, "start");
      complete.outcome = outcome;
      session->sink->publish(std::move(complete));
      session->sink->on_complete(outcome);
    });
    return handle;
  }
  std::vector<std::pair<std::string, FileInput>> files;
  {
    std::lock_guard lock(session->mutex);
    session->call_reservation_active = true;
    session->query = std::move(request.query);
    session->query_defined = true;
    session->matching = true;
    session->input_closed = true;
    for (auto &[key, file] : unique_files) {
      session->files.emplace_back(key, file);
      files.emplace_back(key, std::move(file));
      session->scheduled[key] = true;
      ++session->accepted_files;
    }
    session->fresh_profiles = claims;
    for (const auto &[key, _] : claims)
      session->claimed_profiles.insert(key);
  }
  auto *raw_impl = impl_.get();
  impl_->enqueue_control([raw_impl, session, handle, files = std::move(files),
                          claims = std::move(claims)]() mutable {
    publish_control(session, "start", "query-defined");
    auto accepted = event(EventKind::Control, "start");
    accepted.action = "files-accepted";
    accepted.accepted_files = accepted_count(session);
    session->sink->publish(std::move(accepted));
    handle->schedule(std::move(files), std::move(claims), "start");
    (void)raw_impl;
  });
  return handle;
}

std::shared_ptr<IQueryHandle>
QueryController::open(std::shared_ptr<IQueryEventSink> sink) {
  auto session = std::make_shared<Impl::Session>(std::move(sink));
  impl_->register_session(session);
  auto handle = std::make_shared<QueryHandle>(impl_, session);
  const auto violations = impl_->analysis.admission.reserve_stream_overhead();
  if (violations.empty()) {
    std::lock_guard lock(session->mutex);
    session->call_reservation_active = true;
    return handle;
  }
  Outcome outcome{OutcomeCode::ResourceExhausted,
                  "stream overhead exceeds session limit", violations};
  {
    std::lock_guard lock(session->mutex);
    session->terminal = true;
    session->terminal_outcome = outcome;
  }
  impl_->enqueue_control([session, outcome] {
    auto rejected = event(EventKind::Rejected, "");
    rejected.outcome = outcome;
    session->sink->publish(std::move(rejected));
    auto complete = event(EventKind::Completed, "");
    complete.outcome = outcome;
    session->sink->publish(std::move(complete));
    session->sink->on_complete(outcome);
  });
  return handle;
}

void QueryController::stop_admission() {
  if (!impl_)
    return;
  impl_->stop_admission();
  for (const auto &session : impl_->live_sessions()) {
    session->cancellation.pause(false);
    QueryHandle(std::shared_ptr<Impl>(impl_.get(), [](Impl *) {}), session,
                false)
        .close_input();
  }
}

namespace {
std::uint64_t
accepted_count(const std::shared_ptr<QueryController::Impl::Session> &session) {
  std::lock_guard lock(session->mutex);
  return session->accepted_files;
}

void release_pending_claims(
    QueryController::Impl *impl,
    const std::shared_ptr<QueryController::Impl::Session> &session) {
  std::vector<std::pair<std::string, FileInput>> claims;
  {
    std::lock_guard lock(session->mutex);
    for (const auto &[key, file] : session->fresh_profiles) {
      if (session->claimed_profiles.erase(key) != 0)
        claims.emplace_back(key, file);
    }
    session->fresh_profiles.clear();
  }
  impl->analysis.admission.rollback(claims);
}

void publish_control(
    const std::shared_ptr<QueryController::Impl::Session> &session,
    const std::string &request_id, const std::string &action) {
  auto update = event(EventKind::Control, request_id);
  update.action = action;
  session->sink->publish(std::move(update));
}

void publish_rejection(
    const std::shared_ptr<QueryController::Impl::Session> &session,
    const QueryCommand &command, Outcome outcome,
    bool complete_initial = false) {
  auto rejected = event(EventKind::Rejected, command.request_id);
  rejected.action =
      command.kind == CommandKind::AddFiles ? "AddFiles" : "Command";
  rejected.outcome = outcome;
  session->sink->publish(std::move(rejected));
  if (complete_initial) {
    bool complete = false;
    std::uint64_t completed_files = 0, match_count = 0;
    {
      std::lock_guard lock(session->mutex);
      if (!session->terminal) {
        session->terminal = true;
        session->terminal_outcome = outcome;
        completed_files = session->completed_files;
        match_count = session->match_count;
        complete = true;
      }
    }
    if (complete) {
      auto done = event(EventKind::Completed, command.request_id);
      done.completed_files = completed_files;
      done.match_count = match_count;
      done.outcome = outcome;
      session->sink->publish(std::move(done));
      session->sink->on_complete(std::move(outcome));
    }
  }
}

void maybe_finish(
    const std::shared_ptr<QueryController::Impl::Session> &session,
    const std::string &request_id) {
  Outcome outcome;
  std::uint64_t completed = 0, matches = 0;
  bool finish = false;
  {
    std::lock_guard lock(session->mutex);
    const bool cancelled = session->cancellation.cancelled();
    if (!session->terminal && session->in_flight == 0 &&
        (cancelled || (session->input_closed && session->matching))) {
      session->terminal = true;
      finish = true;
      outcome = session->terminal_outcome;
      if (cancelled) {
        outcome.code = OutcomeCode::Cancelled;
        outcome.message = "query cancelled";
      }
      completed = session->completed_files;
      matches = session->match_count;
    }
  }
  if (!finish)
    return;
  auto done = event(EventKind::Completed, request_id);
  done.completed_files = completed;
  done.match_count = matches;
  done.outcome = outcome;
  session->sink->publish(std::move(done));
  session->sink->on_complete(std::move(outcome));
}

void run_files(QueryController::Impl *impl,
               const std::shared_ptr<QueryController::Impl::Session> &session,
               std::vector<std::pair<std::string, FileInput>> files,
               const std::string &request_id) {
  auto started = event(EventKind::Started, request_id);
  started.accepted_files = accepted_count(session);
  session->sink->publish(std::move(started));
  std::size_t processed = 0;
  for (; processed < files.size();) {
    if (!session->cancellation.checkpoint())
      break;
    auto &[key, file] = files[processed++];
    file.path = normalize_path(file);
    auto progress = event(EventKind::Progress, request_id);
    progress.file = file.path;
    progress.profile = key;
    progress.accepted_files = accepted_count(session);
    session->sink->publish(std::move(progress));

    const auto profile_gate = impl->analysis.profile_mutex(key);
    std::unique_lock profile_guard(*profile_gate);
    Outcome failure;
    ctk::clang_layer::QueryResult result;
    try {
      if (!impl->analysis.engine) {
        failure.code = OutcomeCode::FailedPrecondition;
        failure.message = "native Clang analysis is unavailable in this build";
      } else {
        result = impl->analysis.engine->match(
            {file.path, file.compile_arguments, file.working_directory},
            session->query, [&] { return session->cancellation.checkpoint(); },
            [&](const ctk::clang_layer::IQueryEngine::Bindings &bindings) {
              auto found = event(EventKind::Match, request_id);
              found.file = file.path;
              found.profile = key;
              for (const auto &[name, binding] : bindings) {
                found.bindings.emplace(
                    name,
                    SemanticBinding{binding.kind, binding.name, binding.type});
              }
              {
                std::lock_guard lock(session->mutex);
                found.match_count = ++session->match_count;
                found.completed_files = session->completed_files;
              }
              if (!session->sink->publish(std::move(found)))
                session->cancellation.cancel();
            });
        if (!result.ok) {
          failure.code = result.cancelled ? OutcomeCode::Cancelled
                                          : OutcomeCode::InvalidArgument;
          failure.message = result.message;
        }
      }
    } catch (const std::exception &error) {
      failure.code = OutcomeCode::Internal;
      failure.message = error.what();
    } catch (...) {
      failure.code = OutcomeCode::Internal;
      failure.message = "native analysis failed with an unknown error";
    }

    bool release_claim = false;
    {
      std::lock_guard lock(session->mutex);
      release_claim = session->claimed_profiles.erase(key) != 0;
      std::erase_if(session->fresh_profiles,
                    [&](const auto &item) { return item.first == key; });
    }
    impl->analysis.admission.reconcile(
        profile_key(file), result.native_memory_bytes, result.snapshot_retained,
        release_claim, result.snapshot_evicted);
    profile_guard.unlock();

    std::uint64_t completed = 0;
    {
      std::lock_guard lock(session->mutex);
      if (failure.code != OutcomeCode::Cancelled)
        ++session->completed_files;
      completed = session->completed_files;
      if (failure.code != OutcomeCode::Ok &&
          failure.code != OutcomeCode::Cancelled &&
          session->terminal_outcome.code == OutcomeCode::Ok) {
        session->terminal_outcome = failure;
      }
      if (session->in_flight > 0)
        --session->in_flight;
    }
    auto done = event(EventKind::Progress, request_id);
    done.file = file.path;
    done.profile = key;
    done.completed_files = completed;
    done.accepted_files = accepted_count(session);
    done.outcome = failure;
    session->sink->publish(std::move(done));
  }
  const auto unstarted = files.size() - processed;
  if (unstarted != 0) {
    std::vector<std::pair<std::string, FileInput>> abandoned_claims;
    {
      std::lock_guard lock(session->mutex);
      session->in_flight -= std::min(session->in_flight, unstarted);
      for (std::size_t index = processed; index < files.size(); ++index) {
        const auto &item = files[index];
        if (session->claimed_profiles.erase(item.first) != 0) {
          abandoned_claims.push_back(item);
        }
        std::erase_if(session->fresh_profiles, [&](const auto &fresh) {
          return fresh.first == item.first;
        });
      }
    }
    impl->analysis.admission.rollback(abandoned_claims);
  }
  maybe_finish(session, request_id);
}
} // namespace

void QueryHandle::schedule(
    std::vector<std::pair<std::string, FileInput>> files,
    std::vector<std::pair<std::string, FileInput>> rollback_files,
    const std::string &request_id) {
  if (files.empty()) {
    finish_if_ready(request_id);
    return;
  }
  {
    std::lock_guard lock(session_->mutex);
    session_->in_flight += files.size();
  }
  auto *impl = impl_.get();
  auto session = session_;
  const auto rollback_size = files.size();
  const auto scheduled_copy = files;
  auto rollback_copy = rollback_files;
  auto launch = std::make_shared<std::promise<void>>();
  auto ready = launch->get_future().share();
  if (impl_->enqueue([impl, session, files = std::move(files), request_id,
                      ready]() mutable {
        ready.wait();
        run_files(impl, session, std::move(files), request_id);
      })) {
    auto queued = event(EventKind::Queued, request_id);
    queued.accepted_files = accepted_count(session_);
    queued.pending_requests = impl_->pending_count();
    try {
      if (!session_->sink->publish(std::move(queued))) {
        session_->cancellation.cancel();
      }
    } catch (...) {
      // Always release the worker gate; otherwise a throwing sink could strand
      // an accepted request and prevent session completion forever.
      launch->set_value();
      throw;
    }
    launch->set_value();
    return;
  }
  {
    std::lock_guard lock(session_->mutex);
    session_->in_flight -= rollback_size;
  }
  impl_->analysis.admission.rollback(rollback_copy);
  {
    std::lock_guard lock(session_->mutex);
    for (const auto &[key, _] : rollback_copy) {
      session_->claimed_profiles.erase(key);
      std::erase_if(session_->fresh_profiles,
                    [&](const auto &item) { return item.first == key; });
    }
    for (const auto &[key, _] : scheduled_copy) {
      session_->scheduled.erase(key);
      const auto it =
          std::find_if(session_->files.begin(), session_->files.end(),
                       [&](const auto &item) { return item.first == key; });
      if (it != session_->files.end()) {
        session_->files.erase(it);
        if (session_->accepted_files > 0)
          --session_->accepted_files;
      }
    }
  }
  auto rejected = event(EventKind::Rejected, request_id);
  rejected.action = "executor";
  rejected.outcome.code = OutcomeCode::ResourceExhausted;
  rejected.outcome.message =
      "pending request queue is full or admission is stopped";
  session_->sink->publish(std::move(rejected));
  if (session_->initial_request) {
    std::lock_guard lock(session_->mutex);
    session_->terminal_outcome = {
        OutcomeCode::ResourceExhausted,
        "pending request queue is full or admission is stopped",
        {}};
  }
  finish_if_ready(request_id);
}

void QueryHandle::finish_if_ready(const std::string &request_id) {
  maybe_finish(session_, request_id);
}

void QueryHandle::submit(QueryCommand command,
                         std::function<void()> on_consumed) {
  auto *impl = impl_.get();
  auto session = session_;
  auto callback =
      std::make_shared<std::function<void()>>(std::move(on_consumed));
  auto called = std::make_shared<std::atomic<bool>>(false);
  auto consumed = [callback, called] {
    if (called->exchange(true) || !*callback)
      return;
    try {
      (*callback)();
    } catch (...) {
    }
  };
  if (!impl_->enqueue_control(
          [impl, session, command = std::move(command), consumed]() mutable {
            try {
              QueryHandle dispatcher_handle(
                  std::shared_ptr<QueryController::Impl>(
                      impl, [](QueryController::Impl *) {}),
                  session, false);
              dispatcher_handle.process_command(std::move(command));
            } catch (...) {
              consumed();
              throw;
            }
            consumed();
          }))
    consumed();
}

void QueryHandle::process_command(QueryCommand command) {
  if (!session_->sink)
    return;
  if (command.kind == CommandKind::StartQuery) {
    if (command.query.empty()) {
      Outcome error{OutcomeCode::InvalidArgument,
                    "query expression must not be empty",
                    {}};
      publish_rejection(session_, command, error, session_->initial_request);
      return;
    }
    bool already_defined = false;
    {
      std::lock_guard lock(session_->mutex);
      if (session_->query_defined || session_->terminal) {
        already_defined = true;
      } else {
        session_->query = std::move(command.query);
        session_->query_defined = true;
      }
    }
    if (already_defined) {
      Outcome error{OutcomeCode::FailedPrecondition,
                    "query can be defined only once per stream",
                    {}};
      publish_rejection(session_, command, std::move(error));
      return;
    }
    publish_control(session_, command.request_id, "query-defined");
    return;
  }

  if (command.kind == CommandKind::AddFiles) {
    bool invalid_state = false;
    {
      std::lock_guard lock(session_->mutex);
      if (!session_->query_defined || session_->input_closed ||
          session_->terminal) {
        invalid_state = true;
      }
    }
    if (invalid_state) {
      Outcome error{OutcomeCode::FailedPrecondition,
                    "files require an open stream with a defined query",
                    {}};
      publish_rejection(session_, command, std::move(error));
      return;
    }
    std::unordered_map<std::string, FileInput> unique;
    for (auto file : command.files) {
      file.path = normalize_path(file);
      unique.try_emplace(profile_key(file), std::move(file));
    }
    std::vector<std::pair<std::string, FileInput>> request_files;
    {
      std::lock_guard lock(session_->mutex);
      for (const auto &[key, file] : unique) {
        const auto known =
            std::find_if(session_->files.begin(), session_->files.end(),
                         [&](const auto &entry) { return entry.first == key; });
        if (known == session_->files.end())
          request_files.emplace_back(key, file);
      }
    }
    std::vector<FileInput> reservation_inputs;
    reservation_inputs.reserve(request_files.size());
    for (const auto &entry : request_files)
      reservation_inputs.push_back(entry.second);
    std::vector<std::pair<std::string, FileInput>> fresh;
    auto violations =
        impl_->analysis.admission.reserve_batch(reservation_inputs, fresh);
    if (!violations.empty()) {
      Outcome error{OutcomeCode::ResourceExhausted,
                    "file batch exceeds session limits", std::move(violations)};
      publish_rejection(session_, command, error, session_->initial_request);
      if (session_->initial_request)
        finish_if_ready(command.request_id);
      return;
    }

    std::vector<std::pair<std::string, FileInput>> newly_accepted;
    {
      std::lock_guard lock(session_->mutex);
      for (auto &[key, file] : request_files) {
        session_->files.emplace_back(key, file);
        newly_accepted.emplace_back(key, std::move(file));
        ++session_->accepted_files;
      }
      session_->fresh_profiles.insert(session_->fresh_profiles.end(),
                                      fresh.begin(), fresh.end());
      for (const auto &[key, _] : fresh)
        session_->claimed_profiles.insert(key);
    }
    auto accepted = event(EventKind::Control, command.request_id);
    accepted.action = "files-accepted";
    accepted.accepted_files = accepted_count(session_);
    session_->sink->publish(std::move(accepted));
    bool is_matching = false;
    {
      std::lock_guard lock(session_->mutex);
      is_matching = session_->matching;
      if (is_matching) {
        for (const auto &[key, _] : newly_accepted)
          session_->scheduled[key] = true;
      }
    }
    if (is_matching && !newly_accepted.empty()) {
      schedule(std::move(newly_accepted), std::move(fresh), command.request_id);
    }
    return;
  }

  if (command.kind == CommandKind::Match) {
    std::vector<std::pair<std::string, FileInput>> work;
    std::vector<std::pair<std::string, FileInput>> rollback_files;
    std::optional<Outcome> invalid_command;
    {
      std::lock_guard lock(session_->mutex);
      if (!session_->query_defined || session_->terminal) {
        invalid_command =
            Outcome{OutcomeCode::FailedPrecondition,
                    "Match requires a defined query on an active stream",
                    {}};
      } else if (session_->matching) {
        invalid_command = Outcome{OutcomeCode::FailedPrecondition,
                                  "matching has already started",
                                  {}};
      } else {
        session_->matching = true;
        for (const auto &item : session_->files) {
          if (!session_->scheduled.contains(item.first)) {
            session_->scheduled[item.first] = true;
            work.push_back(item);
          }
        }
        rollback_files = session_->fresh_profiles;
      }
    }
    if (invalid_command) {
      publish_rejection(session_, command, std::move(*invalid_command));
      return;
    }
    publish_control(session_, command.request_id, "matching");
    schedule(std::move(work), std::move(rollback_files), command.request_id);
    return;
  }

  if (command.kind == CommandKind::Pause ||
      command.kind == CommandKind::Resume) {
    const bool pause = command.kind == CommandKind::Pause;
    session_->cancellation.pause(pause);
    publish_control(session_, command.request_id, pause ? "paused" : "resumed");
  }
}

void QueryHandle::close_input() {
  auto *impl = impl_.get();
  auto session = session_;
  impl_->enqueue_control([impl, session] {
    bool no_match = false;
    std::uint64_t completed_files = 0, match_count = 0;
    {
      std::lock_guard lock(session->mutex);
      session->input_closed = true;
      no_match = !session->matching && !session->terminal;
      if (no_match) {
        session->terminal = true;
        session->terminal_outcome = {
            OutcomeCode::FailedPrecondition,
            "Match was not requested before input closed",
            {}};
        completed_files = session->completed_files;
        match_count = session->match_count;
      }
    }
    if (no_match)
      release_pending_claims(impl, session);
    publish_control(session, "", "input-closed");
    if (no_match) {
      auto done = event(EventKind::Completed, "");
      done.completed_files = completed_files;
      done.match_count = match_count;
      done.outcome = session->terminal_outcome;
      session->sink->publish(std::move(done));
      session->sink->on_complete(session->terminal_outcome);
    } else {
      maybe_finish(session, {});
    }
  });
}

void QueryHandle::cancel() {
  session_->cancellation.cancel();
  auto *impl = impl_.get();
  auto session = session_;
  impl_->enqueue_control([impl, session] {
    bool idle = false;
    {
      std::lock_guard lock(session->mutex);
      idle = session->in_flight == 0;
    }
    if (idle)
      release_pending_claims(impl, session);
    maybe_finish(session, {});
  });
}

void QueryHandle::reject(std::string request_id, Outcome outcome,
                         std::function<void()> on_consumed) {
  auto session = session_;
  auto callback =
      std::make_shared<std::function<void()>>(std::move(on_consumed));
  auto called = std::make_shared<std::atomic<bool>>(false);
  auto consumed = [callback, called] {
    if (called->exchange(true) || !*callback)
      return;
    try {
      (*callback)();
    } catch (...) {
    }
  };
  if (!impl_->enqueue_control([session, request_id = std::move(request_id),
                               outcome = std::move(outcome),
                               consumed]() mutable {
        try {
          auto rejected = event(EventKind::Rejected, request_id);
          rejected.outcome = std::move(outcome);
          session->sink->publish(std::move(rejected));
        } catch (...) {
          consumed();
          throw;
        }
        consumed();
      }))
    consumed();
}

void QueryHandle::transport_done() {
  if (owns_call_)
    impl_->release_call(session_);
}

} // namespace ctk::application
