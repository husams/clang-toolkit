#include "embedded_services.hpp"

#include "ctk/application/batch_registry.hpp"
#include "ctk/application/match_controller.hpp"
#include "ctk/application/project_index.hpp"
#include "ctk/application/query.hpp"
#include "ctk/platform/index_worker.hpp"
#include "ctk/storage/root_lock.hpp"
#include "documents.hpp"
#include "semantic.hpp"
#include "value_access.hpp"

#include <algorithm>
#include <array>
#include <condition_variable>
#include <cstdlib>
#include <filesystem>
#include <limits>
#include <mutex>
#include <random>

#include <google/protobuf/util/json_util.h>
#include <llvm/ADT/StringExtras.h>
#include <llvm/ADT/StringSwitch.h>
#include <llvm/Support/JSON.h>

namespace ctk::jit {
namespace {

namespace fs = std::filesystem;
namespace index_api = ctk::index::v1;
namespace batch_api = ctk::analysis::v1;
namespace match_api = ctk::match::v1;
namespace app = ctk::application;
using clang_layer::MatchCode;
using namespace value_access;

const std::string owner = "ctk-jit";

const char* environment(const char* name) {
  const auto* value = std::getenv(name);
  return value && *value ? value : nullptr;
}

fs::path state_root() {
  if (const auto* path = environment("CTK_JIT_STATE_DIR"))
    return fs::absolute(path);
  if (const auto* path = environment("XDG_STATE_HOME"))
    return fs::path(path) / "ctk-jit";
  if (const auto* home = environment("HOME"))
    return fs::path(home) / ".local/state/ctk-jit";
  throw std::runtime_error("set CTK_JIT_STATE_DIR to use indexes or durable batches");
}

fs::path index_worker() {
  const auto sibling = platform::current_executable_sibling("ctk-index-worker");
  if (fs::is_regular_file(sibling))
    return sibling;
  return CTK_JIT_INDEX_WORKER;
}

template <typename Message> const Message* message(const Value& value) {
  const auto* proto = semantic_message(value);
  if (!proto || proto->GetDescriptor() != Message::descriptor())
    return nullptr;
  return static_cast<const Message*>(proto);
}

template <typename Message> Value view(Message message) {
  return {semantic(std::make_unique<Message>(std::move(message)))};
}

template <typename Message>
const Value* show(Values& runtime, Message message, bool display, std::string output) {
  if (display && !emit_text(runtime, output))
    return nullptr;
  return runtime.hold(view(std::move(message)));
}

const std::string& string_arg(const Sequence& args, std::size_t index) {
  if (index < args.items.size()) {
    if (const auto* text = as<std::string>(args.items[index]))
      return *text;
  }
  throw std::invalid_argument("operation requires a string argument");
}

std::string local_path(llvm::StringRef path) {
  if (path.starts_with("~/") || path == "~") {
    if (const auto* home = environment("HOME"))
      return (fs::path(home) / path.drop_front(std::min<std::size_t>(2, path.size())).str())
          .lexically_normal()
          .string();
    throw std::invalid_argument("HOME is unavailable for project path");
  }
  return fs::absolute(path.empty() ? fs::path(".") : fs::path(path.str()))
      .lexically_normal()
      .string();
}

std::string project_name(const index_api::ProjectIndexStatus& status) {
  if (!status.project_name().empty())
    return status.project_name();
  auto base = fs::path(status.project_root()).filename().string();
  return base.empty() ? status.project_root() : base;
}

std::string resolve_project(app::ProjectIndexController& index, llvm::StringRef text) {
  if (text.empty() || text == "." || text == ".." || text.starts_with("~") || text.contains('/'))
    return local_path(text);
  auto projects = index.list();
  std::string root;
  for (const auto& item : projects.projects()) {
    if (project_name(item) != text)
      continue;
    if (!root.empty())
      throw std::invalid_argument("ambiguous project name " + text.str() + "; use a full path");
    root = item.project_root();
  }
  if (root.empty())
    throw std::invalid_argument("no indexed project named " + text.str() +
                                "; use an explicit path");
  return root;
}

std::string index_status(const index_api::ProjectIndexStatus& status) {
  std::string output;
  llvm::raw_string_ostream out(output);
  out << "Project index "
      << llvm::StringRef(index_api::IndexState_Name(status.state()))
             .drop_front(sizeof("INDEX_STATE_") - 1)
      << "\nName  " << project_name(status) << "\nProject  " << status.project_root()
      << "\nSaved index  " << status.translation_units_indexed() << " files"
      << "\nRevision " << status.revision();
  if (status.state() == index_api::INDEX_STATE_IDLE)
    out << "\nCurrent pass  Not running";
  else {
    out << "\nCurrent pass checked  "
        << status.translation_units_completed() + status.translation_units_failed() << '/'
        << status.translation_units_total() << "\nCurrent pass reused   "
        << status.translation_units_skipped() << "\nCurrent pass extracting "
        << status.translation_units_indexing() << "\nCurrent pass remaining  "
        << status.translation_units_pending() << "\nCurrent pass failed   "
        << status.translation_units_failed();
  }
  if (status.has_last_completed_pass()) {
    const auto& pass = status.last_completed_pass();
    out << "\nLast pass total " << pass.total() << "; reused " << pass.reused()
        << "; newly indexed " << pass.newly_indexed() << "; failed " << pass.failed();
  } else
    out << "\nLast completed pass  Not recorded";
  if (!status.current_translation_unit().empty())
    out << "\nCurrent  " << status.current_translation_unit();
  if (!status.paused_reason().empty())
    out << '\n' << status.paused_reason();
  if (!status.error().empty())
    out << '\n' << status.error();
  return output;
}

std::string symbol_lines(const index_api::FindSymbolsResponse& result) {
  std::string output;
  llvm::raw_string_ostream out(output);
  out << "Symbol index revision " << result.revision() << (result.stale() ? " (stale)" : "");
  for (const auto& symbol : result.symbols()) {
    out << '\n'
        << symbol.qualified_name() << "  [" << symbol.kind() << "]  " << symbol.file_path() << ':'
        << symbol.line() << ':' << symbol.column();
  }
  if (result.symbols().empty())
    out << "\nNo symbols in the indexed coverage.";
  if (result.truncated())
    out << "\nResults truncated at 100 matches; narrow the name prefix.";
  return output;
}

const Value* index_command(Values& runtime, app::ProjectIndexController& index,
                           llvm::StringRef command, const Sequence& args, llvm::StringRef options,
                           llvm::StringRef database, bool display) {
  if (command == "index_list") {
    auto result = index.list();
    std::string text;
    if (display) {
      llvm::raw_string_ostream out(text);
      out << "Indexed projects";
      for (const auto& item : result.projects())
        out << '\n' << project_name(item) << "  " << item.project_root();
      if (result.projects().empty())
        out << "\nNo indexed projects.";
      out << "\nTotal projects: " << result.total_count();
    }
    return show(runtime, std::move(result), display, std::move(text));
  }
  const auto& first = string_arg(args, 0);
  if (command == "index_find") {
    index_api::FindSymbolsRequest request;
    const auto parsed = google::protobuf::util::JsonStringToMessage(options.str(), &request);
    if (!parsed.ok())
      return runtime.fail(parsed.ToString());
    llvm::StringRef query(first);
    if (request.match_mode() == index_api::FindSymbolsRequest::MATCH_MODE_PREFIX) {
      query.consume_back("*");
      if (query.empty() || query.find_first_of("*?[]") != llvm::StringRef::npos)
        return runtime.fail("use a nonempty name prefix with an optional trailing *");
    }
    request.set_query(query.str());
    if (args.items.size() > 1 && string_arg(args, 1) != "*") {
      request.set_project_root(resolve_project(index, string_arg(args, 1)));
      auto result = index.find(request);
      auto text = display ? symbol_lines(result) : std::string{};
      return show(runtime, std::move(result), display, std::move(text));
    }
    auto projects = index.list();
    std::vector<Value> entries;
    std::string text;
    llvm::raw_string_ostream out(text);
    if (display)
      out << "Symbol search across " << projects.projects_size() << " projects";
    for (const auto& project : projects.projects()) {
      request.set_project_root(project.project_root());
      auto row = std::make_shared<Record>();
      row->set("project_root", {project.project_root()});
      if (display)
        out << "\nProject  " << project.project_root();
      try {
        auto found = index.find(request);
        if (display)
          out << '\n' << symbol_lines(found);
        row->set("result", view(std::move(found)));
        row->set("error", {std::string{}});
      } catch (const std::exception& error) {
        if (display)
          out << "\nSearch failed: " << error.what();
        row->set("result", {});
        row->set("error", {std::string(error.what())});
      }
      entries.push_back({std::move(row)});
    }
    if (display && entries.empty())
      out << "\nNo indexed projects.";
    if (display && !emit_text(runtime, text))
      return nullptr;
    return runtime.hold(list(std::move(entries)));
  }
  if (command == "index_lookup") {
    index_api::LookupSymbolRequest request;
    request.set_usr(first);
    request.set_project_root(resolve_project(index, string_arg(args, 1)));
    auto result = index.lookup(request);
    auto text = display ? symbol_lines(result) : std::string{};
    return show(runtime, std::move(result), display, std::move(text));
  }

  index_api::ProjectIndexStatus status;
  if (command == "index_start") {
    index_api::StartProjectIndexRequest request;
    request.set_project_root(local_path(first));
    request.set_compile_commands(database.str());
    if (args.items.size() > 1)
      request.set_project_name(string_arg(args, 1));
    status = index.start(request);
  } else {
    const auto root = resolve_project(index, first);
    if (command == "index_status")
      status = index.status(root);
    else if (command == "index_rename") {
      index_api::RenameProjectIndexRequest request;
      request.set_project_root(root);
      request.set_project_name(string_arg(args, 1));
      status = index.rename(request);
    } else {
      const auto action = llvm::StringSwitch<app::IndexAction>(command)
                              .Case("index_pause", app::IndexAction::Pause)
                              .Case("index_resume", app::IndexAction::Resume)
                              .Default(app::IndexAction::Cancel);
      status = index.control(root, action);
    }
  }
  auto text = display ? index_status(status) : std::string{};
  return show(runtime, std::move(status), display, std::move(text));
}

std::string batch_summary(const batch_api::BatchRun& run) {
  std::size_t completed = 0, failed = 0;
  for (const auto& group : run.groups()) {
    completed += group.state() == "completed";
    failed +=
        group.state() == "failed" || group.state() == "cancelled" || group.state() == "unknown";
  }
  std::string result;
  llvm::raw_string_ostream out(result);
  out << "batch " << run.run_id() << ": " << run.state() << ", revision " << run.revision() << ", "
      << completed << '/' << run.groups_size() << " groups complete, " << failed << " failed";
  return result;
}

const batch_api::ScriptValue* final_value(const batch_api::BatchGroup& group) {
  const batch_api::ScriptValue* result = nullptr;
  if (group.state() == "completed") {
    for (const auto& emission : group.result().emissions())
      if (emission.name() == "__final__")
        result = &emission.value();
  }
  return result;
}

Value promote(const batch_api::ScriptValue& value, unsigned depth, std::size_t& items) {
  if (!items || depth >= 64)
    throw std::invalid_argument("durable batch promotion exceeds the value limit");
  --items;
  switch (value.value_case()) {
  case batch_api::ScriptValue::kScalar: {
    const auto& scalar = value.scalar();
    switch (scalar.value_case()) {
    case batch_api::ScriptScalar::kText:
      return {scalar.text()};
    case batch_api::ScriptScalar::kInteger:
      return {scalar.integer()};
    case batch_api::ScriptScalar::kNumber:
      return {scalar.number()};
    case batch_api::ScriptScalar::kBoolean:
      return {scalar.boolean()};
    default:
      return {};
    }
  }
  case batch_api::ScriptValue::kList: {
    std::vector<Value> result;
    for (const auto& entry : value.list().values())
      result.push_back(promote(entry, depth + 1, items));
    return list(std::move(result));
  }
  case batch_api::ScriptValue::kObject: {
    auto result = std::make_shared<Record>();
    for (const auto& [key, entry] : value.object().fields())
      result->set(key, promote(entry, depth + 1, items));
    return {std::move(result)};
  }
  case batch_api::ScriptValue::kMatches: {
    std::vector<Value> rows;
    for (const auto& row : value.matches().rows()) {
      if (!items)
        throw std::invalid_argument("durable batch promotion exceeds the value limit");
      --items;
      rows.push_back(view(row));
    }
    return list(std::move(rows));
  }
  case batch_api::ScriptValue::kTraversal:
    return view(value.traversal());
  case batch_api::ScriptValue::kCfg:
    return view(value.cfg());
  case batch_api::ScriptValue::kCallGraph:
    return view(value.call_graph());
  case batch_api::ScriptValue::kTree:
    return view(value.tree());
  case batch_api::ScriptValue::kFiles:
    return view(value.files());
  default:
    return {};
  }
}

const Value* batch_command(Values& runtime, app::BatchRegistry& registry, llvm::StringRef command,
                           const Sequence& args, llvm::StringRef options, bool display) {
  batch_api::BatchRun run;
  std::string detail;
  if (command == "durable_batch") {
    const auto* manifest =
        args.items.empty() ? nullptr : message<match_api::DiscoverFilesResponse>(args.items[0]);
    if (!manifest)
      return runtime.fail("durable batch input must be a FileSet created with files");
    batch_api::StartBatchRequest request;
    const auto parsed = google::protobuf::util::JsonStringToMessage(options.str(), &request);
    if (!parsed.ok())
      return runtime.fail(parsed.ToString());
    *request.mutable_inputs() = manifest->inputs();
    if (args.items.size() > 1 && !std::holds_alternative<std::monostate>(args.items[1].data))
      request.set_memory_bytes(parse_batch_memory(string_arg(args, 1)));
    if (args.items.size() > 2 && !std::holds_alternative<std::monostate>(args.items[2].data)) {
      request.set_request_id(string_arg(args, 2));
      if (request.request_id().empty())
        return runtime.fail("request id cannot be empty");
    } else
      request.set_request_id(new_batch_id());
    if (registry.start(request, owner, run, detail) != MatchCode::Ok)
      return runtime.fail(detail);
  } else {
    const auto* previous =
        args.items.empty() ? nullptr : message<batch_api::BatchRun>(args.items[0]);
    batch_api::BatchRunRequest request;
    request.set_run_id(previous ? previous->run_id() : string_arg(args, 0));
    if (command == "batch_promote" || command == "batch_status" || !previous) {
      if (command == "batch_promote" && previous)
        run = *previous;
      else if (registry.status(request, owner, run, detail) != MatchCode::Ok)
        return runtime.fail(detail);
    }
    if (command == "batch_promote") {
      std::vector<Value> promoted;
      std::size_t items = max_items, bytes = 1000000;
      for (const auto& group : run.groups()) {
        if (const auto* final = final_value(group)) {
          const auto used = final->ByteSizeLong();
          if (used > bytes)
            return runtime.fail("durable batch promotion exceeds 1000000 bytes");
          bytes -= used;
          promoted.push_back(promote(*final, 0, items));
        }
      }
      if (display && !emit_text(runtime, "promoted " + std::to_string(promoted.size()) +
                                             " detached batch group result(s)"))
        return nullptr;
      return runtime.hold(list(std::move(promoted), true));
    }
    if (command != "batch_status") {
      batch_api::BatchControlRequest control;
      control.set_run_id(request.run_id());
      control.set_expected_revision(previous ? previous->revision() : run.revision());
      const auto code = command == "batch_cancel"   ? registry.cancel(control, owner, run, detail)
                        : command == "batch_resume" ? registry.resume(control, owner, run, detail)
                                                    : registry.retry(control, owner, run, detail);
      if (code != MatchCode::Ok)
        return runtime.fail(detail);
    }
  }
  auto text = display ? batch_summary(run) : std::string{};
  return show(runtime, std::move(run), display, std::move(text));
}

class QueryEvents final : public app::IQueryEventSink {
public:
  explicit QueryEvents(EmbeddedServices::EventSink emit) : emit_(std::move(emit)) {}

  bool publish(app::QueryEvent event) override {
    if (!emit_)
      return true;
    std::string text;
    llvm::raw_string_ostream out(text);
    out << '[' << event.request_id << "] ";
    switch (event.kind) {
    case app::EventKind::Progress:
      out << event.file << ": " << event.completed_files << '/' << event.accepted_files << " files";
      break;
    case app::EventKind::Match: {
      out << '{';
      bool first = true;
      for (const auto& [name, value] : event.bindings) {
        if (!std::exchange(first, false))
          out << ", ";
        out << llvm::json::Value(name) << ": {\"kind\": " << llvm::json::Value(value.kind)
            << ", \"name\": " << llvm::json::Value(value.name)
            << ", \"type\": " << llvm::json::Value(value.type) << '}';
      }
      out << '}';
      break;
    }
    case app::EventKind::Completed:
      out << "completed: " << event.match_count << " matches";
      break;
    case app::EventKind::Rejected:
      out << "rejected: " << event.outcome.message;
      break;
    case app::EventKind::Control:
      out << "control";
      break;
    case app::EventKind::Queued:
      out << "queued";
      break;
    case app::EventKind::Started:
      out << "started";
      break;
    }
    emit_(std::move(text));
    return true;
  }

  void on_complete(app::Outcome) override {
    {
      std::lock_guard lock(mutex_);
      done_ = true;
    }
    changed_.notify_all();
  }

  bool done() {
    std::lock_guard lock(mutex_);
    return done_;
  }

  void wait_until(std::chrono::steady_clock::time_point deadline) {
    std::unique_lock lock(mutex_);
    changed_.wait_until(lock, deadline, [&] { return done_; });
  }

private:
  EmbeddedServices::EventSink emit_;
  std::mutex mutex_;
  std::condition_variable changed_;
  bool done_ = false;
};

struct QueryStream {
  std::shared_ptr<app::IQueryHandle> handle;
  std::shared_ptr<QueryEvents> events;
};

app::FileInput query_input(const Value& value, const LocalState& settings) {
  if (const auto* input = message<match_api::InputDescriptor>(value)) {
    const auto& profile = input->profile();
    return {input->file_path(),
            {profile.compile_arguments().begin(), profile.compile_arguments().end()},
            profile.working_directory(),
            profile.compilation_database()};
  }
  if (const auto* path = as<std::string>(value))
    return {*path, settings.compilation_arguments, fs::current_path().string(),
            settings.compilation_database};
  throw std::invalid_argument("background query requires a path or file list");
}

std::vector<app::FileInput> query_files(Values& runtime, const Sequence& args,
                                        const LocalState& settings) {
  const auto* configured = object<Sequence>(settings.default_targets);
  if (args.items.size() > 1 || (configured && !configured->items.empty())) {
    const auto& target = args.items.size() > 1 ? args.items[1] : settings.default_targets;
    const auto manifest = semantic_length(target) ? semantic_iteration(target) : std::nullopt;
    if (const auto* items = object<Sequence>(manifest ? *manifest : target)) {
      std::vector<app::FileInput> files;
      for (const auto& item : items->items)
        files.push_back(query_input(item, settings));
      return files;
    }
    return {query_input(target, settings)};
  }
  if (const auto* arg = runtime.lookup("arg")) {
    if (const auto* values = object<Record>(*arg)) {
      const auto file = values->fields.find("file");
      if (file != values->fields.end())
        return {query_input(file->second, settings)};
    }
  }
  return {};
}

} // namespace

std::string new_batch_id() {
  std::random_device random;
  std::array<std::uint8_t, 16> bytes;
  for (auto& byte : bytes)
    byte = static_cast<std::uint8_t>(random());
  return llvm::toHex(bytes, true);
}

std::uint64_t parse_batch_memory(llvm::StringRef text) {
  text = text.trim();
  const auto amount = text.take_while([](char c) { return c >= '0' && c <= '9'; });
  const auto unit = text.drop_front(amount.size()).trim().lower();
  const auto scale = llvm::StringSwitch<std::uint64_t>(unit)
                         .Case("b", 1)
                         .Case("kib", 1024)
                         .Case("mib", 1024 * 1024)
                         .Case("gib", 1024ULL * 1024 * 1024)
                         .Default(0);
  std::uint64_t count;
  if (!scale || amount.getAsInteger(10, count) || !count ||
      count > std::numeric_limits<std::uint64_t>::max() / scale)
    throw std::invalid_argument("memory must use a positive value such as \"768MiB\"");
  return count * scale;
}

struct EmbeddedServices::Impl {
  Impl(std::shared_ptr<clang_layer::IQueryEngine> engine, app::MatchController& matches,
       EventSink events)
      : engine(std::move(engine)), matches(matches), events(std::move(events)) {}

  std::shared_ptr<clang_layer::IQueryEngine> engine;
  app::MatchController& matches;
  EventSink events;
  std::unique_ptr<storage::RootLock> state_lock;
  fs::path root;
  std::unique_ptr<app::ProjectIndexController> index;
  std::unique_ptr<app::ScriptController> scripts;
  std::unique_ptr<app::BatchRegistry> batches;
  std::unique_ptr<app::QueryController> query;
  QueryStream session;
  std::vector<QueryStream> background;
  std::uint64_t next_request = 0;
  bool session_closed = false;
  bool session_paused = false;
  std::string session_label;

  const fs::path& owned_root() {
    if (!state_lock) {
      root = state_root();
      state_lock = std::make_unique<storage::RootLock>(root);
    }
    return root;
  }

  const Value* query_command(Values& runtime, llvm::StringRef command, const Sequence& args,
                             const LocalState& settings, bool display);
};

EmbeddedServices::EmbeddedServices(std::shared_ptr<clang_layer::IQueryEngine> engine,
                                   app::MatchController& matches, EventSink events)
    : impl_(std::make_unique<Impl>(std::move(engine), matches, std::move(events))) {}
EmbeddedServices::~EmbeddedServices() = default;

app::ScriptController& EmbeddedServices::scripts() {
  if (!impl_->scripts) {
    app::CursorSettings settings;
    settings.resources = impl_->matches.resource_manager();
    impl_->scripts = std::make_unique<app::ScriptController>(settings, impl_->engine);
  }
  return *impl_->scripts;
}

const Value* EmbeddedServices::Impl::query_command(Values& runtime, llvm::StringRef command,
                                                   const Sequence& args, const LocalState& settings,
                                                   bool display) {
  if (command == "session_label") {
    session_label = string_arg(args, 0);
    return runtime.hold({});
  }
  if (!query)
    query = std::make_unique<app::QueryController>(app::ControllerSettings{}, engine);
  if (command == "background") {
    const auto* matcher = args.items.empty() ? nullptr : as<MatcherValue>(args.items.front());
    if (!matcher)
      return runtime.fail("background requires a matcher expression");
    std::erase_if(background, [](const QueryStream& stream) { return stream.events->done(); });
    if (background.size() >= 100)
      return runtime.fail("too many active background queries");
    auto sink = std::make_shared<QueryEvents>(events);
    auto handle = query->start({matcher->text, query_files(runtime, args, settings)}, sink);
    background.push_back({std::move(handle), std::move(sink)});
    if (display && !emit_text(runtime, "background query started"))
      return nullptr;
    return runtime.hold({});
  }
  if (session_closed)
    return runtime.fail("interactive query session is closed");
  if (!session.handle) {
    session.events = std::make_shared<QueryEvents>(events);
    session.handle = query->open(session.events);
  }
  if (command == "session_close") {
    session.handle->close_input();
    session_closed = true;
  } else {
    app::QueryCommand request;
    request.request_id = std::to_string(++next_request);
    request.kind = llvm::StringSwitch<app::CommandKind>(command)
                       .Case("session_start", app::CommandKind::StartQuery)
                       .Case("session_add", app::CommandKind::AddFiles)
                       .Case("session_pause", app::CommandKind::Pause)
                       .Case("session_resume", app::CommandKind::Resume)
                       .Default(app::CommandKind::Match);
    if (request.kind == app::CommandKind::StartQuery)
      request.query = string_arg(args, 0);
    if (request.kind == app::CommandKind::AddFiles)
      request.files.push_back(query_input(args.items.at(0), settings));
    if (request.kind == app::CommandKind::Pause || request.kind == app::CommandKind::Resume)
      session_paused = request.kind == app::CommandKind::Pause;
    session.handle->submit(std::move(request));
  }
  const auto output =
      "session " + command.drop_front(sizeof("session_") - 1).str() + " command sent";
  if (display && !emit_text(runtime, output))
    return nullptr;
  return runtime.hold({output});
}

const Value* EmbeddedServices::execute(Values& runtime, llvm::StringRef command,
                                       const Sequence& args, llvm::StringRef options,
                                       const LocalState& settings, bool display) {
  try {
    if (command.starts_with("index_")) {
      if (!impl_->index)
        impl_->index = std::make_unique<app::ProjectIndexController>(
            impl_->owned_root(), std::function<bool()>{}, index_worker());
      return index_command(runtime, *impl_->index, command, args, options,
                           settings.compilation_database, display);
    }
    if (command == "durable_batch" || command.starts_with("batch_")) {
      if (!impl_->batches)
        impl_->batches = std::make_unique<app::BatchRegistry>(
            scripts(), impl_->matches.resource_manager(), impl_->owned_root());
      return batch_command(runtime, *impl_->batches, command, args, options, display);
    }
    return impl_->query_command(runtime, command, args, settings, display);
  } catch (const std::exception& error) {
    return runtime.fail(error.what());
  }
}

bool EmbeddedServices::index_status(index::v1::ListProjectIndexesResponse& response) const {
  if (!impl_->index)
    return false;
  response = impl_->index->list();
  return true;
}

void EmbeddedServices::finish() {
  const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(15);
  if (impl_->session.events && impl_->session_closed && !impl_->session_paused)
    impl_->session.events->wait_until(deadline);
  for (const auto& stream : impl_->background)
    stream.events->wait_until(deadline);
}

} // namespace ctk::jit
