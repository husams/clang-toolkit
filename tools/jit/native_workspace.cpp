#include "native_workspace.hpp"
#include "completion.hpp"
#include "grammar/help.hpp"
#include "grammar/syntax.hpp"
#include "platform/repl_cancellation.hpp"
#include "workspace_display.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <condition_variable>
#include <deque>
#include <filesystem>
#include <fstream>
#include <map>
#include <mutex>
#include <string_view>
#include <thread>

#include <clang/ASTMatchers/Dynamic/Parser.h>
#include <clang/ASTMatchers/Dynamic/Registry.h>
#include <ftxui/component/app.hpp>
#include <ftxui/component/component.hpp>
#include <ftxui/dom/elements.hpp>
#include <ftxui/screen/terminal.hpp>
#include <google/protobuf/descriptor.h>
#include <google/protobuf/message.h>
#include <google/protobuf/util/json_util.h>
#include <llvm/ADT/STLExtras.h>
#include <llvm/ADT/StringMap.h>
#include <llvm/ADT/StringSet.h>
#include <llvm/Support/Base64.h>
#include <llvm/Support/FormatVariadic.h>
#include <llvm/Support/Process.h>
#include <llvm/Support/raw_ostream.h>

namespace ctk::jit {
namespace {

namespace fs = std::filesystem;
namespace json = llvm::json;
namespace tui = ftxui;
namespace display = workspace_display;

std::string as_json(const json::Value &value) {
  return llvm::formatv("{0}", value).str();
}

std::string label(const json::Value &value) {
  if (const auto text = value.getAsString())
    return text->str();
  if (const auto *fields = value.getAsObject()) {
    const auto type = fields->getString("kind");
    const auto *data = fields->get("data");
    if (type && data) {
      if (const auto size = fields->getInteger("length"))
        return llvm::formatv("{0} ({1})", *type, *size).str();
      if (const auto text = data->getAsString())
        return type->str() + " " + text->str();
      return type->str();
    }
  }
  return as_json(value);
}

json::Value decode_message(const json::Object &wire) {
  const auto type = wire.getString("type");
  const auto data = wire.getString("data");
  if (!type || !data)
    return nullptr;
  const auto *descriptor =
      google::protobuf::DescriptorPool::generated_pool()->FindMessageTypeByName(
          type->str());
  if (!descriptor)
    return nullptr;
  auto *factory = google::protobuf::MessageFactory::generated_factory();
  const auto *prototype = factory->GetPrototype(descriptor);
  if (!prototype)
    return nullptr;
  std::vector<char> decoded;
  if (auto error = llvm::decodeBase64(*data, decoded)) {
    llvm::consumeError(std::move(error));
    return nullptr;
  }
  std::unique_ptr<google::protobuf::Message> message(prototype->New());
  if (!message->ParseFromArray(decoded.data(), decoded.size()))
    return nullptr;
  std::string text;
  if (!google::protobuf::util::MessageToJsonString(*message, &text).ok())
    return nullptr;
  auto result = json::parse(text);
  if (!result) {
    llvm::consumeError(result.takeError());
    return nullptr;
  }
  return std::move(*result);
}

struct Source {
  fs::path path;
  unsigned line = 1;
  unsigned column = 1;

  bool operator==(const Source &) const = default;
};

struct Row {
  std::string text;
  std::optional<std::int64_t> preview;
  std::optional<Source> source;
  std::string branch;
  std::optional<std::int64_t> page;
  std::string attach;
  std::string close;
  char action = 0;
  bool markdown = false;
  std::string completion;
  std::string print;
  unsigned depth = 0;
  std::optional<std::int64_t> tree;
  unsigned line = 0;
  bool error = false;
};

struct Panel {
  std::vector<Row> rows;
  std::size_t selected = 0;
  tui::Box bounds;
  std::vector<tui::Box> row_boxes;
  std::size_t column = 0;
  std::size_t scroll_extent = 0;
  tui::Box scroll_track{1, 0, 1, 0};

  void replace(std::vector<Row> next) {
    rows = std::move(next);
    selected = rows.empty() ? 0 : std::min(selected, rows.size() - 1);
  }

  void move(int offset) {
    if (rows.empty())
      return;
    selected = static_cast<std::size_t>(std::clamp(
        static_cast<std::int64_t>(selected) + offset, std::int64_t{0},
        static_cast<std::int64_t>(rows.size() - 1)));
  }

  const Row *current() const {
    return selected < rows.size() ? &rows[selected] : nullptr;
  }
};

struct TreeState {
  llvm::StringSet<> expanded;
  json::Object pages;
};

struct Mailbox {
  std::mutex mutex;
  std::condition_variable available;
  std::deque<json::Object> requests;
  std::deque<json::Object> replies;
  bool closed = false;

  void send(json::Object object) {
    {
      std::lock_guard lock(mutex);
      requests.push_back(std::move(object));
    }
    available.notify_one();
  }

  std::optional<json::Object> receive() {
    std::unique_lock lock(mutex);
    available.wait(lock, [&] { return closed || !requests.empty(); });
    if (closed)
      return std::nullopt;
    auto message = std::move(requests.front());
    requests.pop_front();
    return message;
  }

  void stop() {
    {
      std::lock_guard lock(mutex);
      closed = true;
    }
    available.notify_one();
  }
};

enum class Focus {
  Editor,
  Transcript,
  Files,
  Side,
  Menu,
  Completion,
  Source,
  Matches
};

enum class Reply {
  Command,
  Bindings,
  Resources,
  Status,
  Preview,
  Batch,
  Completion
};

class WorkspaceScreen {
public:
  explicit WorkspaceScreen(llvm::StringRef file)
      : file(file.str()), app(tui::App::Fullscreen()) {}

  llvm::Error run(llvm::StringRef database, const LoadTarget &load,
                  const ScriptArguments &arguments) {
    app.ForceHandleCtrlC(false);
    append("CTK console");
    tui::InputOption options;
    options.multiline = true;
    options.cursor_position = &editor_cursor;
    options.transform = [](tui::InputState state) {
      return std::move(state.element) | tui::color(tui::Color::CyanLight);
    };
    auto editor = tui::Input(&draft, "Enter CTK", options);
    auto renderer = tui::Renderer(editor, [&] {
      drain();
      return render(editor);
    });
    auto controls = tui::CatchEvent(
        renderer, [&](const auto &event) { return dispatch(editor, event); });
    std::jthread ticker([&](std::stop_token stop) {
      std::mutex mutex;
      std::unique_lock lock(mutex);
      std::condition_variable_any tick;
      while (!stop.stop_requested()) {
        tick.wait_for(lock, stop, std::chrono::seconds(2),
                      [] { return false; });
        if (!stop.stop_requested())
          app.PostEvent(tui::Event::Special("ctk-workspace-tick"));
      }
    });

    ReplIO io{
        [this] { return mailbox.receive(); },
        [this](json::Object reply) { deliver(std::move(reply)); },
    };
    std::string fatal;
    std::thread worker([&] {
      try {
        auto result = repl_ir(file, database, load, arguments, &io);
        if (result)
          fatal = llvm::toString(std::move(result));
      } catch (const std::exception &error) {
        fatal = error.what();
      }
      if (!fatal.empty())
        deliver(json::Object{{"fatal", fatal}});
    });
    auto finish = [&] {
      ticker.request_stop();
      ticker.join();
      mailbox.stop();
      worker.join();
    };
    llvm::outs() << "\x1b[?2004h";
    llvm::outs().flush();
    try {
      app.Loop(controls);
    } catch (...) {
      llvm::outs() << "\x1b[?2004l";
      llvm::outs().flush();
      request_repl_cancellation();
      finish();
      throw;
    }
    llvm::outs() << "\x1b[?2004l";
    llvm::outs().flush();
    finish();
    if (!fatal.empty())
      return llvm::createStringError(llvm::inconvertibleErrorCode(), "%s",
                                     fatal.c_str());
    return llvm::Error::success();
  }

private:
  void deliver(json::Object reply) {
    {
      std::lock_guard lock(mailbox.mutex);
      mailbox.replies.push_back(std::move(reply));
    }
    app.PostEvent(tui::Event::Custom);
  }

  void request(Reply purpose, json::Object body,
               std::optional<std::int64_t> tree = {}) {
    if (!ready)
      return;
    pending.emplace_back(purpose, tree);
    mailbox.send(std::move(body));
  }

  void append(llvm::StringRef text, std::optional<std::int64_t> preview = {},
              bool markdown = false, bool script = false, bool error = false) {
    llvm::SmallVector<llvm::StringRef, 8> lines;
    text.split(lines, '\n', -1, script || markdown);
    unsigned number = 0;
    for (auto line : lines) {
      constexpr std::size_t limit = 200000;
      line = line.take_back(std::min(line.size(), limit));
      transcript.rows.push_back({line.str(), preview, {}});
      transcript.rows.back().markdown = markdown;
      transcript.rows.back().line = script ? ++number : 0;
      transcript.rows.back().error = error;
      transcript_bytes += line.size();
      std::size_t remove = 0;
      while (transcript_bytes > limit ||
             transcript.rows.size() - remove > 5000) {
        if (const auto id = transcript.rows[remove].preview)
          result_trees.erase(*id);
        if (!transcript.rows[remove].tree)
          transcript_bytes -= transcript.rows[remove].text.size();
        ++remove;
      }
      while (remove < transcript.rows.size() && transcript.rows[remove].tree &&
             !result_trees.contains(*transcript.rows[remove].tree))
        ++remove;
      if (remove) {
        transcript.rows.erase(transcript.rows.begin(),
                              transcript.rows.begin() + remove);
        transcript.selected =
            transcript.selected >= remove ? transcript.selected - remove : 0;
      }
    }
    if (follow && !transcript.rows.empty())
      transcript.selected = transcript.rows.size() - 1;
  }

  void submit() {
    if (busy || closing || !ready) {
      status = ready ? "A command is running" : "Starting local runtime";
      return;
    }
    if (llvm::StringRef(draft).trim().empty())
      return;
    auto source = std::exchange(draft, {});
    editor_cursor = 0;
    undo.clear();
    append(source, {}, false, true);
    history.push_back(source);
    history_position = history.size();
    const auto [slot, fresh] = commands.try_emplace(source, next_slot);
    if (fresh)
      ++next_slot;
    json::Object body{
        {"slot", slot->second}, {"workspace", true}, {"history", source}};
    if (fresh)
      body["source"] = source;
    last_source = source;
    active_source = std::move(source);
    active_new = fresh;
    busy = true;
    started = std::chrono::steady_clock::now();
    status = "Running";
    request(Reply::Command, std::move(body));
  }

  void panel_request(Reply kind, llvm::StringRef name) {
    if (side_kind == kind && !side_title.empty()) {
      side_title.clear();
      side_requested = false;
      focus = Focus::Editor;
      return;
    }
    side_tree = {};
    side_kind = kind;
    side_title = name.str();
    side_requested = true;
    focus = Focus::Side;
    side.replace({});
    side.column = 0;
    refresh();
  }

  void refresh() {
    if (side_title.empty() || !side_kind)
      return;
    switch (*side_kind) {
    case Reply::Bindings:
      request(Reply::Bindings, projection_request(side_tree));
      break;
    case Reply::Resources:
      request(Reply::Resources, json::Object{{"inspect", "resources"}});
      break;
    case Reply::Status:
      request_status();
      break;
    case Reply::Preview:
    case Reply::Batch:
    case Reply::Command:
    case Reply::Completion:
      break;
    }
  }

  void request_status() {
    if (!busy && std::ranges::none_of(pending, [](const auto &item) {
          return item.first == Reply::Status;
        }))
      request(Reply::Status, json::Object{{"inspect", "status"}});
  }

  static std::optional<std::uint64_t> count_field(const json::Object &value,
                                                  llvm::StringRef name) {
    if (const auto count = value.getInteger(name); count && *count >= 0)
      return static_cast<std::uint64_t>(*count);
    std::uint64_t count = 0;
    if (const auto text = value.getString(name);
        text && !text->getAsInteger(10, count))
      return count;
    return {};
  }

  void read_status(const json::Object &reply) {
    const auto *wire = reply.getObject("value");
    const auto message = wire ? decode_message(*wire) : json::Value(nullptr);
    if (const auto *value = message.getAsObject()) {
      rss = count_field(*value, "residentMemoryBytes");
      sessions = count_field(*value, "activeSessions").value_or(0);
      status_stale = false;
    } else {
      status_stale = true;
    }
  }

  void drain() {
    std::deque<json::Object> replies;
    {
      std::lock_guard lock(mailbox.mutex);
      replies.swap(mailbox.replies);
    }
    for (const auto &reply : replies) {
      if (const auto startup = reply.getString("fatal")) {
        status = startup->str();
        append(*startup);
        busy = false;
        ready = false;
        continue;
      }
      if (const auto error = reply.getString("history_error"))
        append(*error);
      if (reply.getBoolean("ready").value_or(false)) {
        if (const auto *commands = reply.getArray("history")) {
          for (const auto &command : *commands)
            if (const auto text = command.getAsString())
              history.push_back(text->str());
          history_position = history.size();
        }
        ready = true;
        status = "Ready";
        request_status();
        continue;
      }
      if (const auto *progress = reply.getObject("progress")) {
        batch_progress(*progress);
        continue;
      }
      if (const auto *durable = reply.getObject("durable")) {
        durable_progress(*durable);
        continue;
      }
      if (const auto event = reply.getString("event")) {
        auto decoded = json::parse(*event);
        if (decoded) {
          if (const auto *object = decoded->getAsObject()) {
            if (const auto *progress = object->getObject("progress"))
              batch_progress(*progress);
          }
        } else {
          llvm::consumeError(decoded.takeError());
        }
        continue;
      }
      if (reply.getString("history_error"))
        continue;
      if (pending.empty())
        continue;
      const auto [purpose, tree] = pending.front();
      pending.pop_front();
      if (purpose == Reply::Command) {
        busy = false;
        if (batch_total)
          batch_total.reset();
        elapsed = std::chrono::duration<double>(
                      std::chrono::steady_clock::now() - started)
                      .count();
        if (reply.getBoolean("history_cleared").value_or(false)) {
          history.clear();
          history_position = 0;
        }
        const auto error = reply.getString("error").value_or("");
        if (!error.empty()) {
          if (active_new && !reply.getBoolean("compiled").value_or(false))
            commands.erase(active_source);
          status = "Command failed";
          append(error, {}, false, false, true);
        } else {
          status = "Ready";
        }
        const auto output = reply.getString("output").value_or("");
        std::size_t cursor = 0;
        if (const auto *previews = reply.getArray("previews")) {
          for (const auto &preview : *previews) {
            if (const auto *item = preview.getAsObject()) {
              const auto offset =
                  static_cast<std::size_t>(std::max<std::int64_t>(
                      0, item->getInteger("offset").value_or(0)));
              const auto next = std::clamp(offset, cursor, output.size());
              append(output.slice(cursor, next));
              cursor = next;
              const auto markdown = item->getString("markdown").value_or("");
              const auto kind = item->getString("kind").value_or("result");
              auto id = item->getInteger("id");
              if (id && *id < 0)
                id.reset();
              if (markdown.empty())
                append("▸ " + kind.str(), id);
              else
                append(markdown, id, true);
            }
          }
        }
        append(output.drop_front(cursor));
        refresh();
        if (closing || reply.getBoolean("exit").value_or(false))
          app.Exit();
        continue;
      }
      if (purpose == Reply::Batch) {
        if (const auto *value = reply.getObject("value"))
          durable_progress(*value);
        if (const auto error = reply.getString("error");
            error && !error->empty())
          append(*error);
        continue;
      }
      if (purpose == Reply::Completion) {
        finish_completion(reply.get("value"));
      } else if (purpose == Reply::Preview && tree) {
        show_result(*tree, reply.get("value"));
      } else if (purpose == Reply::Status) {
        read_status(reply);
        if (side_kind == purpose)
          show_panel(purpose, reply.get("value"));
      } else if (side_kind == purpose) {
        show_panel(purpose, reply.get("value"));
      }
    }
  }

  void batch_progress(const json::Object &progress) {
    const auto id = progress.getString("run_id").value_or("");
    const auto state = progress.getString("state").value_or("running");
    batch_done = progress.getInteger("done").value_or(0);
    const auto total = progress.getInteger("total").value_or(0);
    batch_total = state == "running" ? std::optional(total) : std::nullopt;
    status =
        llvm::formatv("Batch {0}: {1} {2}/{3}", id, state, batch_done, total)
            .str();
    if (state != "running")
      append(status);
  }

  void fields(std::vector<Row> &rows, const json::Value &data,
              std::string prefix = {}) {
    if (const auto *object = data.getAsObject()) {
      if (const auto *wire_type = object->get("type");
          wire_type && object->get("kind")) {
        const auto decoded = decode_message(*object);
        if (decoded.getAsObject()) {
          fields(rows, decoded, std::move(prefix));
          return;
        }
      }
      for (const auto &[name, value] : *object) {
        const auto title =
            prefix.empty() ? name.str() : prefix + "." + name.str();
        if (value.getAsObject() || value.getAsArray())
          fields(rows, value, title);
        else
          rows.push_back({title + " = " + label(value), {}, {}});
      }
    } else if (const auto *array = data.getAsArray()) {
      for (std::size_t i = 0; i < array->size(); ++i)
        fields(rows, (*array)[i], prefix + "[" + std::to_string(i) + "]");
    } else {
      rows.push_back({prefix + " = " + label(data), {}, {}});
    }
  }

  void source_rows(std::vector<Row> &rows, const json::Value &item) {
    if (const auto *data = item.getAsObject()) {
      if (data->getString("kind") == "match_row") {
        const auto *match = data->getObject("data");
        const auto *bindings = match ? match->getObject("bindings") : nullptr;
        if (bindings) {
          std::vector<llvm::StringRef> names;
          for (const auto &[name, value] : *bindings)
            names.push_back(name);
          std::ranges::sort(names);
          for (const auto name : names)
            if (const auto *binding = bindings->getObject(name))
              if (const auto *location = binding->get("location"))
                source_rows(rows, *location);
        }
        return;
      }
      const auto path = data->getString("path").value_or(
          data->getString("file").value_or(""));
      if (!path.empty()) {
        const auto line =
            std::max<std::int64_t>(1, data->getInteger("line").value_or(1));
        const auto location = fs::path(path.str());
        const auto column =
            std::max<std::int64_t>(1, data->getInteger("column").value_or(1));
        const Source target{location, static_cast<unsigned>(line),
                            static_cast<unsigned>(column)};
        if (std::ranges::none_of(
                rows, [&](const auto &row) { return row.source == target; })) {
          rows.push_back({location.filename().string() + ":" +
                              std::to_string(line) + ":" +
                              std::to_string(column),
                          {},
                          target});
        }
      }
      for (const auto &[key, child] : *data)
        source_rows(rows, child);
    } else if (const auto *items = item.getAsArray()) {
      for (const auto &child : *items)
        source_rows(rows, child);
    }
  }

  json::Object projection_request(const TreeState &tree) const {
    json::Array branches;
    for (const auto &name : tree.expanded)
      branches.emplace_back(name.getKey().str());
    return json::Object{{"inspect", "outline"},
                        {"expanded", std::move(branches)},
                        {"pages", json::Value(json::Object(tree.pages))}};
  }

  void projected_rows(std::vector<Row> &rows, const json::Value &value,
                      llvm::StringRef title, std::string path,
                      const TreeState &tree, unsigned depth = 0) {
    const std::string indent(depth * 2, ' ');
    const auto *object = value.getAsObject();
    const auto length = object ? object->getInteger("length") : std::nullopt;
    const auto *children = object ? object->getArray("data") : nullptr;
    const auto type =
        object ? object->getString("kind").value_or("") : llvm::StringRef();
    const auto open = tree.expanded.contains(path);
    if (length && children) {
      rows.push_back(
          {indent + (open ? "▾ " : "▸ ") + title.str() + " = " + label(value),
           {},
           {},
           path});
      rows.back().print = "print " + path;
      rows.back().depth = depth;
      if (!open)
        return;
      const auto start = object->getInteger("start").value_or(0);
      if (start > 0)
        rows.push_back(
            {indent + "  ‹ Previous page", {}, {}, path, start / 50 - 1});
      if (start > 0)
        rows.back().depth = depth + 1;
      for (std::size_t index = 0; index < children->size(); ++index) {
        const auto &child = (*children)[index];
        if (type == "record") {
          const auto *pair = child.getAsArray();
          if (!pair || pair->size() != 2)
            continue;
          const auto field = (*pair)[0].getAsString().value_or("");
          projected_rows(rows, (*pair)[1], field,
                         path + "[" + as_json(json::Value(field)) + "]", tree,
                         depth + 1);
        } else {
          const auto item = "[" + std::to_string(start + index) + "]";
          projected_rows(rows, child, item, path + item, tree, depth + 1);
        }
      }
      if (start + static_cast<std::int64_t>(children->size()) < *length)
        rows.push_back(
            {indent + "  Next page ›", {}, {}, path, start / 50 + 1});
      if (start + static_cast<std::int64_t>(children->size()) < *length)
        rows.back().depth = depth + 1;
      return;
    }
    rows.push_back({indent + title.str() + " = " + label(value), {}, {}});
    rows.back().print = "print " + path;
    rows.back().depth = depth;
    if (object) {
      const auto begin = rows.size();
      source_rows(rows, value);
      for (auto it = rows.begin() + begin; it != rows.end(); ++it) {
        it->text.insert(0, indent + "  ");
        it->depth = depth + 1;
      }
    }
  }

  void resource_rows(std::vector<Row> &rows, const json::Object &resources) {
    const auto decode = [&](llvm::StringRef key) {
      const auto *wire = resources.getObject(key);
      return wire ? decode_message(*wire) : json::Value(nullptr);
    };
    const auto branch = [&](std::string id, std::string label, unsigned depth) {
      const auto open = side_tree.expanded.contains(id);
      rows.push_back(
          {std::string(depth * 2, ' ') + (open ? "▾ " : "▸ ") + label,
           {},
           {},
           std::move(id)});
      rows.back().depth = depth;
      return open;
    };
    const auto detail = [&](std::string text, unsigned depth) {
      rows.push_back({std::string(depth * 2, ' ') + text, {}, {}});
      rows.back().depth = depth;
    };
    const auto files = decode("files");
    const auto *file_list =
        files.getAsObject() ? files.getAsObject()->getArray("files") : nullptr;
    const auto file_count = file_list ? file_list->size() : 0;
    if (branch(":files",
               llvm::formatv("Open files · file list [{0}]", file_count).str(),
               0)) {
      if (!file_count)
        detail("No open files", 1);
      for (std::size_t i = 0; i < std::min<std::size_t>(file_count, 100); ++i) {
        const auto *file = (*file_list)[i].getAsObject();
        if (!file)
          continue;
        const auto *input = file->getObject("input");
        const auto path = input ? input->getString("filePath").value_or("")
                                : llvm::StringRef();
        const auto lease = file->getString("leaseId").value_or("");
        const auto identity =
            lease.empty() ? file->getString("snapshotId").value_or("") : lease;
        const auto name =
            path.empty() ? "File" : fs::path(path.str()).filename().string();
        const auto open = branch(
            "file:" + identity.str(),
            llvm::formatv("{0} · leases {1} · cursors {2}", name,
                          count_field(*file, "explicitLeases").value_or(0),
                          count_field(*file, "cursorCount").value_or(0))
                .str(),
            1);
        if (!lease.empty())
          rows.back().close = "file close " + as_json(json::Value(lease));
        if (!path.empty())
          rows.back().source = Source{path.str()};
        if (open)
          detail(llvm::formatv(
                     "work {0} · native {1:F1} MiB",
                     count_field(*file, "activeWork").value_or(0),
                     count_field(*file, "accountedNativeBytes").value_or(0) /
                         1048576.0)
                     .str(),
                 2);
      }
    }
    const auto sessions = decode("sessions");
    const auto *session_list =
        sessions.getAsObject() ? sessions.getAsObject()->getArray("sessions")
                               : nullptr;
    const auto session_count = session_list ? session_list->size() : 0;
    if (branch(":sessions",
               llvm::formatv("Retained sessions · session list [{0}]",
                             session_count)
                   .str(),
               0)) {
      if (!session_count)
        detail("No retained sessions", 1);
      for (std::size_t i = 0; i < std::min<std::size_t>(session_count, 100);
           ++i) {
        const auto *session = (*session_list)[i].getAsObject();
        if (!session)
          continue;
        const auto id = session->getString("sessionId").value_or("");
        if (id.empty())
          continue;
        const auto name =
            resources.getString("attach_name").value_or("attached1");
        const auto argument = as_json(json::Value(id));
        const auto open =
            branch("session:" + id.str(),
                   llvm::formatv("{0} · {1} rows", id.take_front(12),
                                 count_field(*session, "rowCount").value_or(0))
                       .str(),
                   1);
        rows.back().attach =
            "session attach " + argument + " into $" + name.str();
        rows.back().close = "session close " + argument;
        if (open)
          detail(llvm::formatv(
                     "{0} · revision {1}",
                     fs::path(session->getString("filePath").value_or("").str())
                         .filename()
                         .string(),
                     count_field(*session, "resultRevision").value_or(0))
                     .str(),
                 2);
      }
    }
    if (file_count > 100 || session_count > 100)
      detail("Inventory limited to 100 of each; use list commands", 0);
  }

  void durable_progress(const json::Object &wire) {
    const auto data = decode_message(wire);
    const auto *run = data.getAsObject();
    if (!run)
      return;
    run_id = run->getString("runId").value_or("").str();
    const auto state = run->getString("status").value_or("unknown");
    status = "Batch " + run_id + " · " + state.str();
    durable_active = state == "queued" || state == "running";
    if (!run_id.empty())
      append(durable_active ? status + " · [Cancel]" : status);
  }

  void cancel_batch() {
    if (busy)
      request_repl_cancellation();
    else if (durable_active)
      request(Reply::Batch,
              json::Object{{"inspect", "batch_cancel"}, {"run_id", run_id}});
  }

  void show_panel(Reply purpose, const json::Value *value) {
    std::vector<Row> rows;
    if (value) {
      if (purpose == Reply::Bindings) {
        if (const auto *bindings = value->getAsObject()) {
          std::vector<llvm::StringRef> names;
          for (const auto &[name, operand] : *bindings)
            names.push_back(name);
          std::ranges::sort(names);
          for (const auto name : names) {
            const auto path = "$" + name.str();
            projected_rows(rows, *bindings->get(name), path, path, side_tree);
          }
        }
      } else if (purpose == Reply::Resources) {
        if (const auto *resources = value->getAsObject())
          resource_rows(rows, *resources);
      } else {
        fields(rows, *value);
      }
    }
    if (rows.empty())
      rows.push_back({"No entries", {}, {}});
    side.replace(std::move(rows));
  }

  void request_result(std::int64_t id) {
    auto query = projection_request(result_trees[id]);
    query["result"] = id;
    request(Reply::Preview, std::move(query), id);
  }

  void show_result(std::int64_t id, const json::Value *value) {
    auto &rows = transcript.rows;
    const auto root = std::ranges::find_if(
        rows, [&](const Row &row) { return row.preview == id; });
    if (root == rows.end())
      return;
    const auto index = static_cast<std::size_t>(root - rows.begin());
    const auto end = std::find_if(
        root + 1, rows.end(), [&](const Row &row) { return row.tree != id; });
    const auto removed = static_cast<std::size_t>(end - root - 1);
    std::vector<Row> children;
    if (const auto state = result_trees.find(id);
        value && state != result_trees.end()) {
      const auto *object = value->getAsObject();
      const auto type =
          object ? object->getString("kind").value_or("") : llvm::StringRef();
      const auto path = type == "matches"  ? "$Matches"
                        : type == "record" ? "$Dictionary"
                                           : "$List";
      if (type == "matches")
        source_rows(children, *value);
      projected_rows(children, *value, path, path, state->second);
      for (auto &row : children) {
        row.text.insert(0, "  ");
        ++row.depth;
        row.tree = id;
        row.print.clear();
      }
    }
    if (root->text.starts_with("▸ ") || root->text.starts_with("▾ "))
      root->text.replace(0, std::string_view("▸").size(),
                         children.empty() ? "▸" : "▾");
    rows.erase(root + 1, end);
    rows.insert(rows.begin() + index + 1,
                std::make_move_iterator(children.begin()),
                std::make_move_iterator(children.end()));
    if (transcript.selected > index + removed)
      transcript.selected = transcript.selected - removed + children.size();
    else if (transcript.selected > index)
      transcript.selected =
          index + std::min(transcript.selected - index, children.size());
  }

  void prepare(std::string command) {
    if (llvm::StringRef(draft).trim().empty())
      set_draft(std::move(command));
    else
      status =
          "Draft kept. Clear it with Ctrl+C before preparing another command.";
    focus = Focus::Editor;
  }

  void list_directory(const fs::path &path, unsigned depth,
                      std::vector<Row> &rows) {
    if (depth >= 32 || rows.size() >= 500)
      return;
    struct Entry {
      fs::path path;
      bool directory;
    };
    std::vector<Entry> entries;
    std::error_code error;
    for (fs::directory_iterator
             item(path, fs::directory_options::skip_permission_denied, error),
         end;
         !error && item != end && entries.size() < 500; item.increment(error)) {
      const auto name = item->path().filename().string();
      const auto type = item->symlink_status(error);
      if (error)
        break;
      const auto directory = fs::is_directory(type);
      if (!show_hidden &&
          (name.starts_with(".") ||
           (directory && (name == "build" || name == "node_modules" ||
                          name == "__pycache__" || name == "vendor"))))
        continue;
      entries.push_back({item->path(), directory});
    }
    std::ranges::sort(entries, [](const Entry &a, const Entry &b) {
      if (a.directory != b.directory)
        return a.directory;
      return llvm::StringRef(a.path.filename().string())
                 .compare_insensitive(b.path.filename().string()) < 0;
    });
    for (const auto &entry : entries) {
      if (rows.size() >= 500)
        break;
      const auto key = entry.path.string();
      const auto open = open_directories.contains(key);
      const auto name = entry.path.filename().string();
      rows.push_back({std::string(depth * 2, ' ') +
                          (entry.directory ? (open ? "▾ " : "▸ ") : "  ") +
                          name,
                      {},
                      Source{entry.path},
                      entry.directory ? key : std::string()});
      rows.back().depth = depth;
      if (open)
        list_directory(entry.path, depth + 1, rows);
    }
  }

  void files() {
    std::vector<Row> rows;
    std::error_code error;
    if (directory.empty())
      directory = fs::current_path(error);
    if (!error)
      list_directory(directory, 0, rows);
    if (rows.empty())
      rows.push_back({error ? error.message() : "No visible files", {}, {}});
    local_files.replace(std::move(rows));
  }

  void activate_file() {
    const auto *row = local_files.current();
    if (!row || !row->source)
      return;
    if (!row->branch.empty()) {
      if (!open_directories.erase(row->branch))
        open_directories.insert(row->branch);
      files();
    } else {
      prepare("parse " + as_json(json::Value(row->source->path.string())));
      if (viewport.dimx < 80)
        files_visible = false;
    }
  }

  void jump_source(const Source &target) {
    std::ifstream source(target.path);
    if (!source) {
      status = "Cannot open " + target.path.string();
      return;
    }
    source_target = target;
    std::vector<Row> lines;
    std::string line;
    for (unsigned i = 1; std::getline(source, line); ++i)
      lines.push_back({llvm::formatv("{0,5} │ {1}", i, line).str(), {}, {}});
    source_code.replace(std::move(lines));
    source_code.selected = 0;
    source_code.column = 0;
    source_code.move(static_cast<int>(target.line) - 1);
  }

  void open_source(Source target, const Panel &panel,
                   std::optional<std::int64_t> tree) {
    std::vector<Row> links;
    for (const auto &row : panel.rows)
      if (row.source && (!tree || row.tree == tree) &&
          std::ranges::none_of(links, [&](const Row &link) {
            return link.source == row.source;
          }))
        links.push_back(row);
    source_matches.replace(std::move(links));
    const auto found =
        std::ranges::find_if(source_matches.rows, [&](const Row &row) {
          return row.source == target;
        });
    source_matches.selected = found == source_matches.rows.end()
                                  ? 0
                                  : found - source_matches.rows.begin();
    jump_source(target);
    if (source_target) {
      source_origin = focus;
      focus = Focus::Source;
    }
  }

  static llvm::StringRef shortcuts() {
    return "## Workspace shortcuts\n\n"
           "F1 Shortcuts · F2 Actions · F3 Files · F4 Help · F5 Refresh · F6 "
           "Focus\n"
           "F7 Outline · F8 Resources · F9 Runtime · F10 Quit\n\n"
           "Enter runs complete input. Ctrl+J runs the whole draft.\n"
           "Ctrl/Option/Alt/Shift+Enter adds an indented line.\n"
           "Tab completes · Ctrl+R searches · Ctrl+C clears or cancels.\n"
           "Right/Left expands or collapses · O opens source · Esc closes.";
  }

  void help() {
    if (side_title == "Command help" && side_visible()) {
      side_title.clear();
      side_requested = false;
      focus = Focus::Editor;
      return;
    }
    side_kind.reset();
    side_title = "Command help";
    side_requested = true;
    focus = Focus::Side;
  }

  void context_help() {
    const auto input = draft.empty()
                           ? llvm::StringRef(last_source)
                           : llvm::StringRef(draft).take_front(editor_cursor);
    auto topic = input.trim().split(' ').first;
    if (topic == "help")
      topic = input.trim().drop_front(4).trim();
    if (const auto *candidate =
            completion_open ? completion.current() : nullptr)
      topic = llvm::StringRef(candidate->completion).rtrim("(");
    else if (const auto call = input.rfind('(');
             call != llvm::StringRef::npos) {
      const auto before = input.take_front(call).rtrim();
      auto begin = before.size();
      while (begin && name_character(before[begin - 1]))
        --begin;
      if (begin < before.size())
        topic = before.drop_front(begin);
    }
    if (topic == help_topic && !side.rows.empty() && side.rows.front().markdown)
      return;
    help_topic = topic.str();
    auto reference = native_help(topic);
    if (topic.empty() ||
        llvm::StringRef(reference.text).starts_with("unknown help topic"))
      reference.markdown =
          "## Workspace\n\n"
          "Write a command below. Ctrl+J runs the whole draft. Enter runs "
          "complete input at its end. Ctrl/Option+Enter adds an indented "
          "line.\n\n"
          "## Panels\n\n"
          "- F3 Local files\n- F4 Command help\n- F7 Binding outline\n"
          "- F8 Resources\n- F9 Local runtime\n\n"
          "F6 changes focus. Ctrl+R searches. F10 quits.";
    std::vector<Row> rows;
    llvm::SmallVector<llvm::StringRef, 64> lines;
    llvm::StringRef(reference.markdown).split(lines, '\n');
    for (const auto line : lines) {
      rows.push_back({line.str(), {}, {}});
      rows.back().markdown = true;
    }
    side.replace(std::move(rows));
    side.selected = 0;
  }

  void insert_draft(llvm::StringRef text) {
    draft.insert(static_cast<std::size_t>(editor_cursor), text.data(),
                 text.size());
    editor_cursor += static_cast<int>(text.size());
  }

  void set_draft(std::string text) {
    draft = std::move(text);
    editor_cursor = static_cast<int>(draft.size());
  }

  struct EditState {
    std::vector<std::size_t> openers;
    llvm::StringRef last;
    bool literal = false;
    bool comment = false;
  };

  static EditState input_state(llvm::StringRef text) {
    EditState state;
    for (const auto &token : display::tokens(text)) {
      const auto word = text.slice(token.begin, token.end);
      if (token.role == display::Role::Comment) {
        state.comment = token.end == text.size();
        continue;
      }
      if (word.trim().empty())
        continue;
      state.last = word;
      state.literal = token.open_literal;
      if (token.role != display::Role::Plain || word.size() != 1)
        continue;
      if (llvm::StringRef("([{").contains(word.front()))
        state.openers.push_back(token.begin);
      else if (!state.openers.empty() &&
               llvm::StringRef(")]}").contains(word.front()))
        state.openers.pop_back();
    }
    return state;
  }

  static llvm::StringRef margin(llvm::StringRef before) {
    if (const auto newline = before.rfind('\n');
        newline != llvm::StringRef::npos)
      before = before.drop_front(newline + 1);
    return before.take_front(before.size() - before.ltrim(" \t").size());
  }

  void insert_newline() {
    const auto at = static_cast<std::size_t>(editor_cursor);
    const auto before = llvm::StringRef(draft).take_front(at);
    const auto state = input_state(before);
    const auto indentation = margin(before).str();
    auto addition = "\n" + indentation;
    constexpr llvm::StringRef open = "([{";
    constexpr llvm::StringRef close = ")]}";
    const auto pair = state.last.size() == 1 ? open.find(state.last.front())
                                             : llvm::StringRef::npos;
    const auto last_line = before.rfind('\n');
    const auto opens_here =
        pair != llvm::StringRef::npos && !state.literal &&
        (last_line == llvm::StringRef::npos ||
         static_cast<std::size_t>(state.last.data() - before.data()) >
             last_line);
    if (opens_here || (state.last == "do" && !state.literal))
      addition += "    ";
    const auto cursor_step = addition.size();
    if (opens_here && at < draft.size() && draft[at] == close[pair])
      addition += "\n" + indentation;
    draft.insert(at, addition);
    editor_cursor += static_cast<int>(cursor_step);
  }

  bool incomplete() const {
    const auto state = input_state(draft);
    return state.literal || !state.openers.empty() || state.last == "|" ||
           state.last == "=" || state.last == "do";
  }

  std::vector<Row> matcher_completions(llvm::StringRef prefix) const {
    const auto input = llvm::StringRef(draft).take_front(editor_cursor);
    const auto match = input.rfind("match ");
    if (match == llvm::StringRef::npos ||
        (match && llvm::StringRef(" =;{\n\t").find(input[match - 1]) ==
                      llvm::StringRef::npos))
      return {};
    auto expression = input.drop_front(match + 6).ltrim();
    if (expression.contains(" in "))
      return {};
    const auto offset = expression.size();
    auto matches = clang::ast_matchers::dynamic::Parser::completeExpression(
        expression, offset);
    std::vector<Row> rows;
    for (const auto &candidate : matches) {
      if (rows.size() == 30)
        break;
      const auto typed = llvm::StringRef(candidate.TypedText);
      auto insertion =
          typed.starts_with(prefix) ? typed.str() : prefix.str() + typed.str();
      rows.push_back({insertion + "  " + candidate.MatcherDecl, {}, {}});
      rows.back().completion = std::move(insertion);
    }
    return rows;
  }

  static bool name_character(char ch) {
    return (ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') ||
           (ch >= '0' && ch <= '9') || ch == '_';
  }

  void open_completion(std::vector<Row> results) {
    if (results.empty())
      return;
    completion_open = true;
    focus = Focus::Completion;
    completion.replace(std::move(results));
    completion.selected = 0;
  }

  struct CompletionQuery {
    std::string draft;
    int cursor;
    std::string prefix;
    std::string suffix;
    std::optional<std::string> reference;
    char quote = 0;
    bool quote_open = false;
  };

  void finish_completion(const json::Value *result) {
    auto query = std::exchange(completion_query, {});
    if (!query || query->draft != draft || query->cursor != editor_cursor ||
        focus != Focus::Editor)
      return;

    std::vector<Row> rows;
    if (query->reference) {
      if (const auto *fields = result ? result->getAsArray() : nullptr) {
        for (const auto &entry : *fields) {
          const auto *field = entry.getAsObject();
          if (!field)
            continue;
          auto name = field->getString("name").value_or("");
          if (!name.starts_with(query->prefix) ||
              !name.ends_with(query->suffix))
            continue;
          if (query->quote) {
            auto insertion = name.str();
            if (!query->quote_open)
              insertion.insert(insertion.begin(), query->quote);
            if (editor_cursor == draft.size() ||
                draft[editor_cursor] != query->quote)
              insertion += query->quote;
            rows.push_back({name.str() + "  field presence", {}, {}});
            rows.back().completion = std::move(insertion);
            continue;
          }
          auto insertion = name.drop_back(query->suffix.size()).str();
          auto display = name.str();
          if (field->getBoolean("method").value_or(false) &&
              query->suffix.empty() &&
              !llvm::StringRef(draft)
                   .drop_front(editor_cursor)
                   .ltrim()
                   .starts_with("(")) {
            insertion += '(';
            display += '(';
          }
          rows.push_back(
              {display + "  " + field->getString("detail").value_or("").str(),
               {},
               {}});
          rows.back().completion = std::move(insertion);
        }
      }
    } else {
      auto candidates = native_help_topics(query->prefix);
      if (const auto *bindings = result ? result->getAsObject() : nullptr)
        for (const auto &[name, unused] : *bindings)
          candidates.push_back(name.str());
      for (auto &candidate : candidates) {
        if (candidate.size() <= 64 &&
            llvm::StringRef(candidate).starts_with_insensitive(query->prefix)) {
          rows.push_back({candidate, {}, {}});
          rows.back().completion = std::move(candidate);
        }
      }
    }
    std::ranges::sort(rows, {}, &Row::text);
    llvm::StringSet<> seen;
    std::erase_if(rows, [&](const Row &row) {
      return !seen.insert(row.completion).second;
    });
    if (!query->reference && rows.size() > 30)
      rows.resize(30);
    open_completion(std::move(rows));
  }

  bool complete_presence() {
    const auto before_cursor = llvm::StringRef(draft).take_front(editor_cursor);
    const auto method = before_cursor.rfind("hasField");
    if (method == llvm::StringRef::npos)
      return false;
    const auto reference = field_receiver(before_cursor.take_front(method));
    if (!reference)
      return false;
    auto argument = before_cursor.drop_front(method + 8).ltrim();
    if (!argument.consume_front("("))
      return false;
    argument = argument.ltrim();
    const bool quoted = argument.starts_with('"') || argument.starts_with('\'');
    const auto quote = quoted ? argument.front() : '"';
    if (quoted)
      argument = argument.drop_front();
    if ((!quoted && !argument.empty()) ||
        !llvm::all_of(argument, name_character))
      return false;

    completion_end = static_cast<std::size_t>(editor_cursor);
    completion_begin = completion_end - argument.size();
    if (ready && !busy) {
      completion_query = CompletionQuery{
          draft, editor_cursor, argument.str(), {}, reference->str(),
          quote, quoted};
      request(Reply::Completion, json::Object{{"inspect", "complete_fields"},
                                              {"reference", reference->str()},
                                              {"presence", true}});
    }
    return true;
  }

  bool complete_path() {
    const auto text = llvm::StringRef(draft);
    const auto cursor = static_cast<std::size_t>(editor_cursor);
    const auto before = text.take_front(cursor);
    const auto tokens = display::tokens(before);
    if (tokens.empty() || tokens.back().role == display::Role::Comment)
      return false;

    constexpr llvm::StringRef separators = " \t\r\n\"'\x60()[]{},;\x24=<>|!";
    const auto separator = before.find_last_of(separators);
    auto begin = separator == llvm::StringRef::npos ? 0 : separator + 1;
    auto end = cursor;
    const auto literal = std::find_if(tokens.rbegin(), tokens.rend(), [&](const auto &token) {
      return token.role == display::Role::String &&
             (token.end == cursor || token.end == begin);
    });
    if (literal != tokens.rend()) {
      begin = literal->begin;
      if (text[begin] == 96)
        return false;
    }
    if (literal != tokens.rend() && literal->open_literal) {
      // Replace the existing suffix and its closing quote as one atom.
      while (end < text.size()) {
        const auto ch = text[end++];
        if (ch == text[begin])
          break;
        if (ch == '\\' && end < text.size())
          ++end;
      }
    } else {
      while (end < text.size() && !separators.contains(text[end]))
        ++end;
    }

    auto role = path_role_after(text.take_front(begin));
    if (role == PathRole::None && begin != cursor && end == cursor &&
        literal == tokens.rend()) {
      // Allow Tab directly after a complete keyword, including parse and files.
      begin = cursor;
      role = path_role_after(before);
    }
    if (role == PathRole::None)
      return false;

    const bool space = begin == cursor &&
                       !llvm::StringRef(" \t\r\n([{,").contains(before.back());
    std::vector<Row> rows;
    for (auto &candidate : path_suggestions(role, text.slice(begin, cursor))) {
      rows.push_back({std::move(candidate.display), {}, {}});
      rows.back().completion = space ? " " + candidate.insertion
                                     : std::move(candidate.insertion);
    }
    if (rows.empty())
      return false;
    completion_begin = begin;
    completion_end = end;
    open_completion(std::move(rows));
    return true;
  }

  void complete() {
    if (completion_open) {
      completion.move(1);
      return;
    }
    if (completion_query || complete_presence() || complete_path())
      return;
    completion_end = static_cast<std::size_t>(editor_cursor);
    completion_begin = completion_end;
    while (completion_begin > 0 && name_character(draft[completion_begin - 1]))
      --completion_begin;
    const auto text = llvm::StringRef(draft);
    const auto prefix = text.slice(completion_begin, completion_end);
    const auto before_word = text.take_front(completion_begin);
    const auto reference = field_receiver(before_word);
    if (!reference) {
      auto matches = matcher_completions(prefix);
      if (!matches.empty()) {
        open_completion(std::move(matches));
        return;
      }
      if (prefix.empty() || before_word.rtrim().ends_with("."))
        return;
    }
    auto suffix_end = completion_end;
    while (suffix_end < draft.size() && name_character(draft[suffix_end]))
      ++suffix_end;
    completion_query = CompletionQuery{
        draft, editor_cursor, prefix.str(),
        text.slice(completion_end, suffix_end).str(),
        reference ? std::optional(reference->str()) : std::nullopt};
    if (!ready || busy) {
      finish_completion(nullptr);
      return;
    }
    if (reference)
      request(Reply::Completion, json::Object{{"inspect", "complete_fields"},
                                              {"reference", reference->str()}});
    else
      request(Reply::Completion, json::Object{{"inspect", "outline"}});
  }

  void accept_completion() {
    if (const auto *row = completion.current()) {
      auto insertion = row->completion;
      const bool opens = llvm::StringRef(insertion).ends_with("(");
      const bool already_open = opens && completion_end < draft.size() &&
                                draft[completion_end] == '(';
      if (already_open)
        insertion.pop_back();
      draft.replace(completion_begin, completion_end - completion_begin,
                    insertion);
      auto cursor = completion_begin + insertion.size();
      if (already_open) {
        ++cursor;
      } else if (opens && (cursor == draft.size() || draft[cursor] != ')')) {
        draft.insert(cursor, 1, ')');
      }
      editor_cursor = static_cast<int>(cursor);
    }
    dismiss_completion();
  }

  bool smart_pair(const tui::Event &event) {
    const auto at = static_cast<std::size_t>(editor_cursor);
    const auto prefix = llvm::StringRef(draft).take_front(at);
    constexpr llvm::StringRef open = "([{'\"";
    constexpr llvm::StringRef close = ")]}'\"";
    if (event == tui::Event::Backspace && at > 0 && at < draft.size()) {
      const auto pair = open.find(draft[at - 1]);
      if (pair != llvm::StringRef::npos && draft[at] == close[pair]) {
        const auto state = input_state(prefix.drop_back());
        if (!state.literal && !state.comment) {
          draft.erase(at - 1, 2);
          --editor_cursor;
          return true;
        }
      }
    }
    if (!event.is_character() || event.character().size() != 1)
      return false;
    const auto ch = event.character().front();
    if (!open.contains(ch) && !close.contains(ch))
      return false;
    const auto state = input_state(prefix);
    if (state.comment)
      return false;
    if (state.literal) {
      if (at < draft.size() && ch == draft[at] && state.last.front() == ch &&
          !prefix.ends_with("\\")) {
        ++editor_cursor;
        return true;
      }
      return false;
    }
    if (const auto pair = close.find(ch);
        pair < 3 && !state.openers.empty() &&
        draft[state.openers.back()] == open[pair]) {
      const auto newline = prefix.rfind('\n');
      const auto start = newline == llvm::StringRef::npos ? 0 : newline + 1;
      if (prefix.drop_front(start).trim().empty()) {
        const auto indentation =
            margin(prefix.take_front(state.openers.back())).str();
        draft.replace(start, at - start, indentation);
        editor_cursor = static_cast<int>(start + indentation.size());
        const auto rest = llvm::StringRef(draft).drop_front(editor_cursor);
        const auto closer = rest.find_first_not_of("\n \t");
        if (closer != llvm::StringRef::npos && rest[closer] == ch)
          draft.erase(editor_cursor, closer);
      }
    }
    if (static_cast<std::size_t>(editor_cursor) < draft.size() &&
        ch == draft[editor_cursor] && close.contains(ch)) {
      ++editor_cursor;
      return true;
    }
    const auto pair = open.find(ch);
    if (pair == llvm::StringRef::npos)
      return false;
    draft.insert(editor_cursor, {ch, close[pair]});
    ++editor_cursor;
    return true;
  }

  void start_search() {
    searching_transcript = focus == Focus::Transcript;
    search_origin = focus;
    saved_cursor = editor_cursor;
    saved_draft = draft;
    set_draft({});
    focus = Focus::Editor;
    searching = true;
    status = searching_transcript ? "Search transcript" : "Search history";
  }

  void restore_search() {
    draft = std::move(saved_draft);
    editor_cursor = saved_cursor;
    searching = false;
    focus = search_origin;
  }

  void accept_search() {
    const auto query = draft;
    restore_search();
    if (searching_transcript) {
      for (std::size_t i = transcript.rows.size(); i > 0; --i) {
        if (llvm::StringRef(transcript.rows[i - 1].text)
                .contains_insensitive(query)) {
          transcript.selected = i - 1;
          follow = false;
          focus = Focus::Transcript;
          status = "Transcript match";
          return;
        }
      }
    } else {
      for (std::size_t i = history.size(); i > 0; --i) {
        if (llvm::StringRef(history[i - 1]).contains_insensitive(query)) {
          set_draft(history[i - 1]);
          history_position = i - 1;
          status = "History match";
          return;
        }
      }
    }
    status = "No matches";
  }

  bool wide_side() const {
    return !side_title.empty() &&
           viewport.dimx >= 64 + side_width() + (wide_files() ? 30 : 0);
  }

  bool wide_files() const { return files_visible && viewport.dimx >= 80; }
  bool side_visible() const {
    return wide_side() || (side_requested && !side_title.empty());
  }
  int side_width() const { return side_title == "Command help" ? 36 : 48; }

  void close_menu() {
    if (menu_visible) {
      menu_visible = false;
      focus = menu_origin;
    }
  }

  void toggle_files() {
    files_visible = !files_visible;
    if (files_visible) {
      files();
      focus = Focus::Files;
    } else {
      focus = Focus::Editor;
    }
  }

  void latest() {
    follow = true;
    transcript.selected =
        transcript.rows.empty() ? 0 : transcript.rows.size() - 1;
  }

  void quit() {
    closing = true;
    if (busy)
      status = "Finishing command before exit";
    else
      app.Exit();
  }

  void toggle_menu() {
    if (menu_visible) {
      close_menu();
      return;
    }
    menu_origin = focus;
    menu_visible = true;
    focus = Focus::Menu;
    std::vector<Row> rows;
    for (const auto &[key, label] :
         std::initializer_list<std::pair<char, std::string>>{
             {'f', files_visible ? "Close local files  F3"
                                 : "Browse local files  F3"},
             {'F', "Refresh files  F5"},
             {'h', show_hidden ? "Hide hidden files" : "Show hidden files"},
             {'l',
              follow ? "Pause following results" : "Resume following results"},
             {'L', "Show latest results"},
             {'s', "Search results  Ctrl+R"},
             {'w', wrap ? "Disable result wrapping" : "Enable result wrapping"},
             {'x', "Clear displayed results"},
             {'H', side_title == "Command help" && side_visible()
                       ? "Hide command help"
                       : "Show command help"},
             {'?', "Workspace shortcuts  F1"},
             {'e', "Prepare console help"},
             {'b', "Binding outline  F7"},
             {'u', "Open files and sessions  F8"},
             {'t', "Live runtime status  F9"},
             {'i', "List open files"},
             {'j', "List retained sessions"},
             {'k', "List bindings"},
             {'v', "Show runtime status"},
             {'r', "Run command  Ctrl+J"},
             {'q', "Quit  F10"},
         }) {
      rows.push_back({label, {}, {}});
      rows.back().action = key;
    }
    menu.replace(std::move(rows));
    menu.selected = 0;
  }

  void menu_action(char action) {
    close_menu();
    switch (action) {
    case 'f':
      toggle_files();
      break;
    case 'F':
      open_directories.clear();
      files();
      break;
    case 'h':
      show_hidden = !show_hidden;
      open_directories.clear();
      files();
      break;
    case 'l':
      if (follow)
        follow = false;
      else
        latest();
      focus = Focus::Editor;
      break;
    case 'L':
      latest();
      break;
    case 's':
      follow = false;
      focus = Focus::Transcript;
      start_search();
      break;
    case 'w':
      wrap = !wrap;
      break;
    case 'x':
      transcript.replace({});
      result_trees.clear();
      transcript_bytes = 0;
      break;
    case 'H':
      help();
      break;
    case '?':
      append(shortcuts(), {}, true);
      focus = Focus::Editor;
      break;
    case 'e':
      prepare("help");
      break;
    case 'b':
      panel_request(Reply::Bindings, "Bindings");
      break;
    case 'u':
      panel_request(Reply::Resources, "Resources");
      break;
    case 't':
      panel_request(Reply::Status, "Runtime status");
      break;
    case 'i':
      prepare("file list");
      break;
    case 'j':
      prepare("session list");
      break;
    case 'k':
      prepare("bindings");
      break;
    case 'v':
      prepare("server status");
      break;
    case 'r':
      focus = Focus::Editor;
      submit();
      break;
    case 'q':
      quit();
      break;
    }
  }

  Panel *focused_panel() {
    switch (focus) {
    case Focus::Editor:
      return nullptr;
    case Focus::Transcript:
      return &transcript;
    case Focus::Files:
      return &local_files;
    case Focus::Side:
      return &side;
    case Focus::Menu:
      return &menu;
    case Focus::Completion:
      return &completion;
    case Focus::Source:
      return &source_code;
    case Focus::Matches:
      return &source_matches;
    }
    return nullptr;
  }

  void cycle_focus(bool reverse) {
    close_menu();
    std::vector<Focus> panes{Focus::Editor, Focus::Transcript};
    if (files_visible)
      panes.push_back(Focus::Files);
    if (side_visible())
      panes.push_back(Focus::Side);
    const auto current = std::ranges::find(panes, focus);
    const auto index = current == panes.end() ? 0 : current - panes.begin();
    focus = panes[(index + (reverse ? panes.size() - 1 : 1)) % panes.size()];
  }

  static void parent_row(Panel &panel, const Row &row) {
    if (!row.depth)
      return;
    for (auto i = panel.selected; i > 0; --i) {
      if (panel.rows[i - 1].depth < row.depth) {
        panel.selected = i - 1;
        return;
      }
    }
  }

  void tree_key(Panel &panel, const tui::Event &event) {
    using tui::Event;
    const auto *row = panel.current();
    if (!row)
      return;
    if (focus == Focus::Files) {
      if (event == Event::CtrlM) {
        activate_file();
      } else if (!row->branch.empty() &&
                 open_directories.contains(row->branch)) {
        if (event == Event::ArrowLeft) {
          open_directories.erase(row->branch);
          files();
        } else if (panel.selected + 1 < panel.rows.size() &&
                   panel.rows[panel.selected + 1].depth > row->depth) {
          panel.move(1);
        }
      } else if (event == Event::ArrowRight && !row->branch.empty()) {
        activate_file();
      } else if (event == Event::ArrowLeft) {
        parent_row(panel, *row);
      }
      return;
    }
    if (focus == Focus::Matches) {
      if (row->source && event != Event::ArrowLeft)
        jump_source(*row->source);
      return;
    }
    if (row->source && row->branch.empty() && event == Event::CtrlM) {
      open_source(*row->source, panel, row->tree);
      return;
    }
    if (row->preview) {
      const auto id = *row->preview;
      if (result_trees.contains(id)) {
        if (event == Event::ArrowRight) {
          if (panel.selected + 1 < panel.rows.size() &&
              panel.rows[panel.selected + 1].tree == id)
            panel.move(1);
        } else {
          result_trees.erase(id);
          show_result(id, nullptr);
        }
      } else if (event != Event::ArrowLeft) {
        auto &tree = result_trees[id];
        for (const auto *path :
             {"$Matches", "$Matches[0]", "$List", "$Dictionary"})
          tree.expanded.insert(path);
        request_result(id);
      }
      return;
    }
    auto &tree = row->tree ? result_trees[*row->tree] : side_tree;
    if (row->page && event != Event::ArrowLeft) {
      tree.pages[row->branch] = *row->page;
    } else if (row->branch.empty() || (event == Event::ArrowLeft &&
                                       !tree.expanded.contains(row->branch))) {
      if (event == Event::ArrowLeft)
        parent_row(panel, *row);
      return;
    } else if (event == Event::ArrowRight &&
               tree.expanded.contains(row->branch)) {
      if (panel.selected + 1 < panel.rows.size() &&
          panel.rows[panel.selected + 1].depth > row->depth)
        panel.move(1);
      return;
    } else if (!tree.expanded.erase(row->branch)) {
      tree.expanded.insert(row->branch);
    }
    if (row->tree)
      request_result(*row->tree);
    else
      refresh();
  }

  bool panel_key(Panel &panel, const tui::Event &event) {
    using tui::Event;
    const auto *row = panel.current();
    if (event == Event::ArrowUp || event == Event::ArrowDown) {
      panel.move(event == Event::ArrowUp ? -1 : 1);
    } else if (event == Event::PageUp || event == Event::PageDown) {
      const auto height = std::max(1, panel.bounds.y_max - panel.bounds.y_min);
      panel.move(event == Event::PageUp ? -height : height);
    } else if (event == Event::Home || event == Event::End) {
      panel.selected = event == Event::Home || panel.rows.empty()
                           ? 0
                           : panel.rows.size() - 1;
    } else if (event == Event::ArrowLeftCtrl ||
               event == Event::ArrowRightCtrl) {
      panel.column = event == Event::ArrowLeftCtrl
                         ? panel.column - std::min<std::size_t>(8, panel.column)
                         : std::min(panel.column + 8, panel.scroll_extent);
    } else if (focus == Focus::Menu && row && event == Event::CtrlM) {
      menu_action(row->action);
      return true;
    } else if (event == Event::CtrlM || event == Event::ArrowLeft ||
               event == Event::ArrowRight) {
      tree_key(panel, event);
      return true;
    } else if (row && row->source && event == Event::Character('o') &&
               focus != Focus::Files) {
      open_source(*row->source, panel, row->tree);
      return true;
    } else if (row && !row->print.empty() && event == Event::Character('p')) {
      prepare(row->print);
      return true;
    } else if (row && !row->attach.empty() && event == Event::Character('a')) {
      prepare(row->attach);
      return true;
    } else if (event == Event::Character('c')) {
      if (row && !row->close.empty())
        prepare(row->close);
      else if (focus == Focus::Transcript)
        cancel_batch();
      return true;
    } else {
      return false;
    }
    if (focus == Focus::Transcript)
      follow = false;
    return true;
  }

  static const auto &toolbar_actions() {
    static const std::array actions{
        std::pair{"Actions [F2] ", tui::Event::F2},
        std::pair{"Help", tui::Event::F4},
        std::pair{"Outline", tui::Event::F7},
        std::pair{"Resources", tui::Event::F8},
        std::pair{"Local runtime", tui::Event::F9},
    };
    return actions;
  }

  bool panel_mouse(Panel &panel, Focus target, const tui::Mouse &mouse) {
    if (panel.scroll_track.Contain(mouse.x, mouse.y) &&
        mouse.button == tui::Mouse::Left &&
        mouse.motion == tui::Mouse::Pressed) {
      const auto width =
          std::max(1, panel.scroll_track.x_max - panel.scroll_track.x_min);
      panel.column =
          panel.scroll_extent * (mouse.x - panel.scroll_track.x_min) / width;
      focus = target;
      return true;
    }
    if (!panel.bounds.Contain(mouse.x, mouse.y))
      return false;
    if (mouse.button == tui::Mouse::WheelUp ||
        mouse.button == tui::Mouse::WheelDown) {
      focus = target;
      panel.move(mouse.button == tui::Mouse::WheelUp ? -3 : 3);
      if (target == Focus::Transcript)
        follow = false;
      return true;
    }
    if (mouse.button == tui::Mouse::Left &&
        mouse.motion == tui::Mouse::Pressed) {
      focus = target;
      for (std::size_t i = 0; i < panel.row_boxes.size(); ++i) {
        const auto &box = panel.row_boxes[i];
        if (!box.Contain(mouse.x, mouse.y))
          continue;
        const auto selected = panel.selected == i;
        panel.selected = i;
        const auto &row = panel.rows[i];
        const auto indent = row.text.find_first_not_of(' ');
        const auto marker =
            indent != std::string::npos &&
            (llvm::StringRef(row.text).drop_front(indent).starts_with("▸") ||
             llvm::StringRef(row.text).drop_front(indent).starts_with("▾"));
        if (target == Focus::Completion)
          accept_completion();
        else if (target == Focus::Menu || selected || row.page ||
                 (row.source && row.branch.empty() && target != Focus::Files) ||
                 (marker && mouse.x == box.x_min + static_cast<int>(indent)))
          return on_event(tui::Event::CtrlM);
        break;
      }
    }
    return true;
  }

  bool on_mouse(const tui::Mouse &mouse) {
    const bool click =
        mouse.button == tui::Mouse::Left && mouse.motion == tui::Mouse::Pressed;
    if (source_target) {
      if (click && source_close_box.Contain(mouse.x, mouse.y))
        close_source();
      else if (click && source_previous_box.Contain(mouse.x, mouse.y))
        step_source(-1);
      else if (click && source_next_box.Contain(mouse.x, mouse.y))
        step_source(1);
      else if (!panel_mouse(source_matches, Focus::Matches, mouse))
        panel_mouse(source_code, Focus::Source, mouse);
      return true;
    }
    if (completion_open && panel_mouse(completion, Focus::Completion, mouse))
      return true;
    if (menu_visible && panel_mouse(menu, Focus::Menu, mouse))
      return true;
    if (click) {
      if ((batch_total || durable_active) &&
          batch_cancel_box.Contain(mouse.x, mouse.y)) {
        cancel_batch();
        return true;
      }
      for (std::size_t i = 0; i < toolbar_boxes.size(); ++i)
        if (toolbar_boxes[i].Contain(mouse.x, mouse.y))
          return on_event(toolbar_actions()[i].second);
      if (side_visible() && side_close_box.Contain(mouse.x, mouse.y)) {
        close_side();
        return true;
      }
      if (files_visible && files_close_box.Contain(mouse.x, mouse.y)) {
        toggle_files();
        return true;
      }
      if (side_visible()) {
        for (std::size_t i = 0; i < side_action_boxes.size(); ++i) {
          if (side_action_boxes[i].Contain(mouse.x, mouse.y))
            return panel_key(side, tui::Event::Character("pac"[i]));
        }
      }
      close_menu();
      if (completion_open)
        dismiss_completion();
    }
    if ((side_visible() && panel_mouse(side, Focus::Side, mouse)) ||
        (files_visible && panel_mouse(local_files, Focus::Files, mouse)) ||
        panel_mouse(transcript, Focus::Transcript, mouse))
      return true;
    if (click && editor_box.Contain(mouse.x, mouse.y)) {
      focus = Focus::Editor;
      if (!searching)
        for (std::size_t i = 0; i < editor_rows.size(); ++i)
          if (editor_rows[i].Contain(mouse.x, mouse.y)) {
            editor_cursor = static_cast<int>(display::offset_at(
                draft, editor_lines[i], mouse.x - editor_rows[i].x_min - 7));
            break;
          }
      return true;
    }
    return false;
  }

  void close_side() {
    side_title.clear();
    side_requested = false;
    focus = Focus::Editor;
  }

  void close_source() {
    source_target.reset();
    focus = source_origin;
  }

  void step_source(int step) {
    source_matches.move(step);
    if (const auto *row = source_matches.current(); row && row->source)
      jump_source(*row->source);
  }

  void dismiss_completion() {
    completion_open = false;
    focus = Focus::Editor;
  }

  static bool modified_enter(const tui::Event &event) {
    const llvm::StringRef key(event.input());
    return key == "\x1b\r" || key == "\x1b\n" ||
           (key.size() == 7 && key.starts_with("\x1b[13;") &&
            llvm::StringRef("2356").contains(key[5]) && key.back() == 'u') ||
           (key.size() == 10 && key.starts_with("\x1b[27;") &&
            llvm::StringRef("2356").contains(key[5]) && key.ends_with(";13~"));
  }

  bool dispatch(const tui::Component &editor, tui::Event event) {
    using tui::Event;
    const bool editing = focus == Focus::Editor || focus == Focus::Completion;
    if (editing && !pasting) {
      if (event == Event::CtrlA)
        event = Event::Home;
      else if (event == Event::CtrlE)
        event = Event::End;
      else if (event == Event::CtrlB)
        event = Event::ArrowLeft;
      else if (event == Event::CtrlF)
        event = Event::ArrowRight;
      else if (event == Event::CtrlP)
        event = Event::ArrowUp;
      else if (event == Event::CtrlN)
        event = Event::ArrowDown;
      else if (event == Event::CtrlD && !draft.empty())
        event = Event::Delete;
      else if (event == Event::Special("\x1b"
                                       "b"))
        event = Event::ArrowLeftCtrl;
      else if (event == Event::Special("\x1b"
                                       "f"))
        event = Event::ArrowRightCtrl;
    }
    std::optional<std::pair<std::string, int>> prior;
    if (editing && !pasting && !searching &&
        (event.is_character() || event == Event::CtrlM ||
         event == Event::Backspace || event == Event::Delete ||
         event == Event::Special("\x1b[200~") || modified_enter(event)))
      prior.emplace(draft, editor_cursor);
    const auto submitted = history.size();
    const auto handled =
        on_event(event) || (focus == Focus::Editor && editor->OnEvent(event));
    if (prior && submitted == history.size() &&
        (prior->first != draft || pasting)) {
      if (undo.size() >= 64)
        undo.pop_front();
      undo.push_back(std::move(*prior));
    }
    return handled;
  }

  bool on_event(tui::Event event) {
    using tui::Event;
    if (event == Event::Custom) {
      drain();
      return true;
    }
    if (event == Event::Special("ctk-workspace-tick")) {
      request_status();
      return true;
    }
    if (event.is_mouse())
      return on_mouse(event.mouse());
    if (event == Event::F10) {
      quit();
      return true;
    }
    if (source_target) {
      if (event == Event::Escape || event == Event::CtrlC)
        close_source();
      else if (event == Event::Tab || event == Event::TabReverse ||
               event == Event::F6)
        focus = focus == Focus::Source ? Focus::Matches : Focus::Source;
      else if (event == Event::Character('n') || event == Event::Character('p'))
        step_source(event == Event::Character('n') ? 1 : -1);
      else
        panel_key(*focused_panel(), event);
      return true;
    }
    if (event == Event::Special("\x1b[200~")) {
      if (completion_open)
        dismiss_completion();
      pasting = true;
      return true;
    }
    if (event == Event::Special("\x1b[201~")) {
      pasting = false;
      pasted_cr = false;
      return true;
    }
    if (pasting) {
      if (focus != Focus::Editor)
        return true;
      if (event == Event::CtrlM || event == Event::CtrlJ) {
        if (!(pasted_cr && event == Event::CtrlJ))
          insert_draft("\n");
        pasted_cr = event == Event::CtrlM;
      } else {
        pasted_cr = false;
        if (event == Event::Tab)
          insert_draft("\t");
        else if (event.is_character())
          insert_draft(event.character());
      }
      return true;
    }
    if (searching) {
      if (event == Event::CtrlM || event == Event::CtrlJ) {
        accept_search();
        return true;
      }
      if (event == Event::Escape || event == Event::CtrlC) {
        restore_search();
        status = "Ready";
        return true;
      }
      return false;
    }
    if (completion_open) {
      if (event == Event::CtrlM) {
        accept_completion();
        return true;
      }
      if (event == Event::Tab || event == Event::TabReverse ||
          event == Event::ArrowUp || event == Event::ArrowDown ||
          event == Event::PageUp || event == Event::PageDown) {
        completion.move(event == Event::PageUp     ? -7
                        : event == Event::PageDown ? 7
                        : event == Event::ArrowUp || event == Event::TabReverse
                            ? -1
                            : 1);
        return true;
      }
      dismiss_completion();
      if (event == Event::Escape)
        return true;
    }
    if (event == Event::F1) {
      close_menu();
      append(shortcuts(), {}, true);
      focus = Focus::Editor;
    } else if (event == Event::F2) {
      toggle_menu();
    } else if (event == Event::F3) {
      close_menu();
      toggle_files();
    } else if (event == Event::F4) {
      close_menu();
      help();
    } else if (event == Event::F5) {
      if (focus == Focus::Side && side_visible())
        refresh();
      else {
        open_directories.clear();
        files();
      }
    } else if (event == Event::F6 || event == Event::Special("\x1b[32~") ||
               event == Event::Special("\x1b[29~") ||
               event == Event::Special("\x1b[17;2~")) {
      cycle_focus(event != Event::F6);
    } else if (event == Event::F7 || event == Event::F8 || event == Event::F9) {
      close_menu();
      if (event == Event::F7)
        panel_request(Reply::Bindings, "Bindings");
      else if (event == Event::F8)
        panel_request(Reply::Resources, "Resources");
      else
        panel_request(Reply::Status, "Runtime status");
    } else if (event == Event::CtrlR) {
      close_menu();
      start_search();
    } else if (event == Event::Escape) {
      completion_query.reset();
      if (menu_visible)
        close_menu();
      else if (focus == Focus::Side && side_visible())
        close_side();
      else if (files_visible)
        toggle_files();
      else
        focus = Focus::Editor;
    } else if (event == Event::CtrlC) {
      if (busy) {
        request_repl_cancellation();
        status = "Cancellation requested";
      } else {
        close_menu();
        set_draft({});
        undo.clear();
        status = "Draft cleared";
        focus = Focus::Editor;
      }
    } else if (auto *panel = focused_panel()) {
      if (focus == Focus::Transcript && (event == Event::Special("\x1b[1;5F") ||
                                         event == Event::Special("\x1b[4;5~")))
        latest();
      else
        panel_key(*panel, event);
    } else if (event == Event::CtrlD && draft.empty()) {
      quit();
    } else if (event == Event::Tab) {
      complete();
    } else if (event == Event::CtrlJ) {
      submit();
    } else if (event == Event::Special("\x1f")) {
      if (!undo.empty()) {
        draft = std::move(undo.back().first);
        editor_cursor = undo.back().second;
        undo.pop_back();
      }
    } else if (event == Event::CtrlM || event == Event::Special("\x1b[13u")) {
      if (busy || closing)
        status = "A command is running; your next draft is kept.";
      else if (static_cast<std::size_t>(editor_cursor) < draft.size() ||
               incomplete())
        insert_newline();
      else
        submit();
    } else if (modified_enter(event)) {
      insert_newline();
    } else if (event == Event::ArrowUp || event == Event::ArrowDown) {
      return editor_vertical(event == Event::ArrowUp ? -1 : 1);
    } else {
      return smart_pair(event);
    }
    return true;
  }

  static std::string markdown_text(llvm::StringRef line) {
    std::string text;
    for (std::size_t i = 0; i < line.size(); ++i) {
      if (line[i] == 96)
        continue;
      if (line.substr(i).starts_with("**")) {
        ++i;
        continue;
      }
      if (line[i] == '[') {
        const auto label_end = line.find("](", i);
        const auto link_end = label_end == llvm::StringRef::npos
                                  ? label_end
                                  : line.find(')', label_end + 2);
        if (link_end != llvm::StringRef::npos) {
          text += line.slice(i + 1, label_end);
          i = link_end;
          continue;
        }
      }
      text += line[i];
    }
    return text;
  }

  tui::Element render_panel(Panel &panel, Focus target, bool wrapping,
                            int width) {
    tui::Elements rows;
    panel.row_boxes.resize(panel.rows.size());
    std::size_t longest = 0;
    for (const auto &row : panel.rows)
      longest = std::max(longest, row.text.size());
    const auto content_width = static_cast<std::size_t>(std::max(1, width));
    panel.scroll_extent = longest - std::min(longest, content_width);
    panel.column = std::min(panel.column, panel.scroll_extent);
    bool code = false;
    unsigned example_line = 0;
    for (std::size_t i = 0; i < panel.rows.size(); ++i) {
      const auto &row = panel.rows[i];
      const auto source = llvm::StringRef(row.text);
      auto text = source;
      auto offset = std::min(panel.column, text.size());
      while (offset < text.size() &&
             (static_cast<unsigned char>(text[offset]) & 0xc0) == 0x80)
        ++offset;
      text = text.drop_front(offset);
      auto element = tui::text(text.str());
      if (row.markdown && source.starts_with(std::string(3, 96))) {
        code = !code;
        example_line = 0;
        element = tui::text("");
      } else if (row.line || (code && row.markdown)) {
        auto lines = display::lines(source, std::max(1, width - 7),
                                    wrapping && panel.column == 0);
        const auto tokens = display::tokens(source);
        lines.front().number = row.line ? row.line : ++example_line;
        if (offset)
          lines.front().begin = offset;
        tui::Elements fragments;
        for (const auto &line : lines)
          fragments.push_back(display::script_line(source, line, tokens) |
                              tui::xflex | tui::bgcolor(tui::Color::Grey15));
        element = tui::vbox(std::move(fragments));
      } else if (row.markdown && source.starts_with("#")) {
        element = tui::paragraph(markdown_text(text.ltrim("# "))) | tui::bold |
                  tui::color(tui::Color::CyanLight);
      } else {
        const auto plain = row.markdown ? markdown_text(text) : text.str();
        if (wrapping && panel.column == 0) {
          tui::Elements fragments;
          const auto text = llvm::StringRef(plain);
          for (const auto &line :
               display::lines(text, std::max(1, width), true))
            fragments.push_back(
                tui::text(text.slice(line.begin, line.end).str()));
          element = tui::vbox(std::move(fragments));
        } else {
          element = tui::text(plain);
        }
        if (row.error)
          element = element | tui::color(tui::Color::RedLight);
        else if (row.source)
          element = element | tui::color(tui::Color::CyanLight);
      }
      if (i == panel.selected) {
        if (focus == target)
          element = element | tui::inverted;
        element = element | tui::focus;
      }
      rows.push_back(std::move(element) | tui::reflect(panel.row_boxes[i]));
    }
    // The selected row anchors this pane's scroll frame. Keep that focus
    // inside the frame so it cannot take the terminal cursor from the editor.
    return tui::vbox(std::move(rows)) | tui::vscroll_indicator | tui::yframe |
           tui::focusPosition(0, 0) | tui::reflect(panel.bounds) | tui::flex;
  }

  std::size_t current_editor_line(std::size_t cursor) const {
    const auto next =
        std::upper_bound(editor_lines.begin(), editor_lines.end(), cursor,
                         [](std::size_t offset, const display::Line &line) {
                           return offset < line.begin;
                         });
    return next == editor_lines.begin() ? 0 : next - editor_lines.begin() - 1;
  }

  bool editor_vertical(int direction) {
    editor_lines = display::lines(draft, editor_text_width, true);
    if (editor_lines.empty())
      return false;
    const auto at = static_cast<std::size_t>(editor_cursor);
    const auto row = current_editor_line(at);
    if (direction < 0 && row == 0) {
      if (history_position > 0)
        set_draft(history[--history_position]);
      return true;
    }
    if (direction > 0 && row + 1 >= editor_lines.size()) {
      if (history_position < history.size()) {
        ++history_position;
        set_draft(history_position < history.size() ? history[history_position]
                                                    : "");
      }
      return true;
    }
    const auto text = llvm::StringRef(draft);
    const auto col = tui::string_width(text.slice(editor_lines[row].begin, at));
    editor_cursor = static_cast<int>(
        display::offset_at(text, editor_lines[row + direction], col));
    return true;
  }

  tui::Element render_editor(int width) {
    const auto source = llvm::StringRef(searching ? saved_draft : draft);
    const auto cursor =
        static_cast<std::size_t>(searching ? saved_cursor : editor_cursor);
    editor_text_width = std::max(1, width - 8);
    editor_lines = display::lines(source, editor_text_width, true);
    editor_rows.resize(editor_lines.size());
    const auto active = current_editor_line(cursor);
    const auto tokens = display::tokens(source);
    tui::Elements rows;
    for (std::size_t i = 0; i < editor_lines.size(); ++i) {
      const bool at_cursor =
          i == active && !searching &&
          (focus == Focus::Editor || focus == Focus::Completion);
      auto line = display::script_line(
          source, editor_lines[i], tokens,
          at_cursor ? std::optional(cursor) : std::nullopt, &cursor_box);
      if (i == active && !at_cursor)
        line = line | tui::focus;
      rows.push_back(std::move(line) | tui::xflex |
                     tui::reflect(editor_rows[i]));
    }
    return tui::vbox(std::move(rows)) | tui::yframe |
           tui::size(tui::HEIGHT, tui::LESS_THAN,
                     std::max(1, (viewport.dimy - 3) / 2)) |
           tui::reflect(editor_box);
  }

  std::string footer() const {
    if (batch_total) {
      const auto done = std::clamp(batch_done, std::int64_t{0},
                                   std::max<std::int64_t>(0, *batch_total));
      const auto filled =
          *batch_total > 0 ? static_cast<int>(12.0 * done / *batch_total) : 0;
      std::string bar;
      for (int i = 0; i < 12; ++i)
        bar += i < filled ? "━" : "─";
      return llvm::formatv(" Batch [{0}] {1}/{2} files", bar, batch_done,
                           *batch_total)
          .str();
    }
    const auto before =
        llvm::StringRef(searching ? saved_draft : draft)
            .take_front(searching ? saved_cursor : editor_cursor);
    const auto line = before.rsplit('\n').second;
    const auto col = before.contains('\n') ? line : before;
    auto text = " Session open | " + status;
    if (busy || elapsed) {
      const auto seconds = busy
                               ? std::chrono::duration<double>(
                                     std::chrono::steady_clock::now() - started)
                                     .count()
                               : *elapsed;
      text += llvm::formatv(" | {0:F1}s", seconds).str();
    }
    text += llvm::formatv(" | Input {0}:{1} | {2}", before.count('\n') + 1,
                          tui::string_width(col) + 1,
                          follow ? "Follow" : "Scroll paused")
                .str();
    if (sessions) {
      const auto memory =
          rss ? llvm::formatv("{0}M", *rss / (1024 * 1024)).str()
              : std::string("unavailable");
      const auto live = llvm::formatv("RSS {0} · Sessions {1}{2}", memory,
                                      *sessions, status_stale ? " · stale" : "")
                            .str();
      text = static_cast<int>(text.size() + live.size() + 3) > viewport.dimx
                 ? " " + status + " | " + live
                 : text + " | " + live;
    }
    return text;
  }

  tui::Element title(llvm::StringRef name, tui::Box &close) {
    return tui::hbox({tui::text(" " + name.str()) | tui::bold,
                      tui::text(" [×] ") | tui::reflect(close)});
  }

  tui::Element horizontal_scroll(Panel &panel, int width) {
    width = std::max(1, width);
    const auto position = panel.scroll_extent
                              ? panel.column * (width - 1) / panel.scroll_extent
                              : 0;
    std::string track;
    for (int i = 0; i < width; ++i)
      track += panel.scroll_extent && static_cast<std::size_t>(i) == position
                   ? "━"
                   : "─";
    return tui::text(std::move(track)) | tui::dim |
           tui::reflect(panel.scroll_track);
  }

  tui::Element render_files(int width) {
    return tui::window(
        title("Local files", files_close_box),
        tui::vbox({tui::text(directory.string()) | tui::dim,
                   render_panel(local_files, Focus::Files, false, width - 2),
                   tui::text("Enter opens · F5 refresh") | tui::dim}),
        tui::LIGHT);
  }

  tui::Element render_side(int width) {
    if (side_title == "Command help")
      context_help();
    const auto heading = side_kind == Reply::Bindings    ? "Bindings · F7"
                         : side_kind == Reply::Resources ? "Resources · F8"
                         : side_kind == Reply::Status    ? "Local runtime · F9"
                                                         : "Command help · F4";
    tui::Elements actions;
    for (auto &box : side_action_boxes)
      box = {1, 0, 1, 0};
    if (const auto *row = side.current()) {
      const std::array available{!row->print.empty(), !row->attach.empty(),
                                 !row->close.empty()};
      const std::array labels{" Print [p] ", " Attach [a] ", " Close [c] "};
      for (std::size_t i = 0; i < labels.size(); ++i)
        if (available[i])
          actions.push_back(tui::text(labels[i]) |
                            tui::color(tui::Color::CyanLight) |
                            tui::reflect(side_action_boxes[i]));
    }
    if (actions.empty())
      actions.push_back(tui::text(" Scroll · F6 focus · × close") | tui::dim);
    tui::Elements body{render_panel(side, Focus::Side,
                                    side_title == "Command help", width - 2)};
    if (side_kind == Reply::Bindings || side_kind == Reply::Resources)
      body.push_back(horizontal_scroll(side, width - 2));
    else
      side.scroll_track = {1, 0, 1, 0};
    body.push_back(tui::hbox(std::move(actions)));
    return tui::window(title(heading, side_close_box),
                       tui::vbox(std::move(body)), tui::LIGHT);
  }

  static tui::Element overlay(tui::Element below, tui::Element above, int x,
                              int y, int width, int height) {
    auto placed = tui::vbox({
        tui::filler() | tui::size(tui::HEIGHT, tui::EQUAL, y),
        tui::hbox({tui::filler() | tui::size(tui::WIDTH, tui::EQUAL, x),
                   std::move(above) | tui::clear_under |
                       tui::size(tui::WIDTH, tui::EQUAL, width),
                   tui::filler()}) |
            tui::size(tui::HEIGHT, tui::EQUAL, height),
        tui::filler(),
    });
    return tui::dbox({std::move(below), std::move(placed)});
  }

  tui::Element render_source() {
    auto tools = tui::hbox({
        tui::text(" ‹ Previous [P] ") | tui::reflect(source_previous_box),
        tui::text(" Next [N] › ") | tui::reflect(source_next_box),
        tui::text(" Tab/F6: code ↔ outline ") | tui::dim,
        tui::filler(),
        tui::text(" Close [Esc] ") | tui::reflect(source_close_box),
    });
    const auto width = viewport.dimx;
    const auto matches_width = std::clamp(width / 4, 20, 48);
    const auto code_width = width - matches_width - 4;
    auto code =
        tui::vbox({render_panel(source_code, Focus::Source, false, code_width),
                   horizontal_scroll(source_code, code_width)}) |
        tui::flex;
    auto matches = tui::vbox({tui::text("Selected match") | tui::bold,
                              render_panel(source_matches, Focus::Matches,
                                           false, matches_width - 2)}) |
                   tui::border |
                   tui::size(tui::WIDTH, tui::EQUAL, matches_width);
    return tui::vbox({
               tui::text(source_target->path.string()) | tui::bold,
               std::move(tools),
               tui::hbox({std::move(code), std::move(matches)}) | tui::flex,
               tui::text(llvm::formatv(" Match · {0}:{1}", source_target->line,
                                       source_target->column)
                             .str()) |
                   tui::dim,
           }) |
           tui::border;
  }

  tui::Element render(const tui::Component &editor) {
    viewport = tui::Terminal::Size();
    if (source_target)
      return render_source();
    const auto [width, height] = viewport;
    const bool files_wide = wide_files();
    const bool side_wide = wide_side();
    const auto center_width = std::max(1, width - (files_wide ? 30 : 0) -
                                              (side_wide ? side_width() : 0));
    const auto lines =
        llvm::StringRef(searching ? saved_draft : draft).count('\n') + 1;
    auto editor_title =
        llvm::formatv(
            " Script · {0} line{1} · Ctrl+J run · Ctrl/Option+Enter newline",
            lines, lines == 1 ? "" : "s")
            .str();
    auto center =
        tui::vbox({
            render_panel(transcript, Focus::Transcript, wrap, center_width - 1),
            tui::text(editor_title) | tui::bgcolor(tui::Color::Grey15),
            render_editor(center_width),
        }) |
        tui::flex;
    tui::Elements columns;
    if (files_wide)
      columns.push_back(render_files(30) |
                        tui::size(tui::WIDTH, tui::EQUAL, 30));
    columns.push_back(std::move(center));
    if (side_wide)
      columns.push_back(render_side(side_width()) |
                        tui::size(tui::WIDTH, tui::EQUAL, side_width()));
    tui::Elements toolbar{tui::text(" CTK console | ") | tui::bold};
    for (std::size_t i = 0; i < toolbar_actions().size(); ++i) {
      if (i)
        toolbar.push_back(tui::text(" | "));
      toolbar.push_back(tui::text(toolbar_actions()[i].first) |
                        tui::reflect(toolbar_boxes[i]));
    }
    tui::Elements screen{
        tui::hbox(std::move(toolbar)) | tui::xframe | tui::xflex |
            tui::bgcolor(tui::Color::Grey15),
        tui::hbox(std::move(columns)) | tui::flex,
    };
    if (searching)
      screen.push_back(tui::hbox({
          tui::text(searching_transcript ? " Search results: "
                                         : " Search history: "),
          editor->Render() | tui::xflex,
      }));
    tui::Elements status_row{tui::text(footer()) | tui::xflex};
    if (batch_total || durable_active)
      status_row.push_back(tui::text(" [Cancel] ") | tui::bold |
                           tui::reflect(batch_cancel_box));
    screen.push_back(tui::hbox(std::move(status_row)) |
                     tui::bgcolor(tui::Color::Grey15));
    auto result = tui::vbox(std::move(screen));
    const auto overlay_height = std::max(3, height - 4);
    if (files_visible && !files_wide)
      result = overlay(std::move(result), render_files(std::min(width, 30)), 0,
                       1, std::min(width, 30), overlay_height);
    if (side_visible() && !side_wide) {
      const auto panel_width = std::min(width, side_width());
      result = overlay(std::move(result), render_side(panel_width),
                       width - panel_width, 1, panel_width, overlay_height);
    }
    if (menu_visible) {
      const auto menu_width = std::min(width, 54);
      auto panel = tui::window(
          tui::text(" Actions · scroll or use arrows ") | tui::bold,
          render_panel(menu, Focus::Menu, false, menu_width - 2), tui::LIGHT);
      result = overlay(std::move(result), std::move(panel), 0, 1, menu_width,
                       std::min(23, std::max(3, height - 3)));
    }
    if (completion_open) {
      const auto popup_width = std::min(width, 60);
      const auto popup_height =
          std::min({10, static_cast<int>(completion.rows.size()) + 3,
                    std::max(3, height - 3)});
      auto popup = tui::vbox({tui::text("Completions") | tui::bold,
                              render_panel(completion, Focus::Completion, false,
                                           popup_width - 2)}) |
                   tui::border | tui::bgcolor(tui::Color::Grey15);
      const auto x = std::clamp(cursor_box.x_min, 0, width - popup_width);
      const auto y = std::clamp(cursor_box.y_min - popup_height, 1,
                                std::max(1, height - popup_height - 2));
      result = overlay(std::move(result), std::move(popup), x, y, popup_width,
                       popup_height);
    }
    return result;
  }

  std::string file;
  tui::App app;
  tui::Dimensions viewport{80, 24};
  Mailbox mailbox;
  std::deque<std::pair<Reply, std::optional<std::int64_t>>> pending;
  std::string draft;
  int editor_cursor = 0;
  std::size_t completion_begin = 0;
  std::size_t completion_end = 0;
  bool completion_open = false;
  std::optional<CompletionQuery> completion_query;
  bool searching = false;
  bool searching_transcript = false;
  std::string saved_draft;
  int saved_cursor = 0;
  Focus search_origin = Focus::Editor;
  std::string active_source;
  std::string last_source;
  std::string help_topic;
  std::string status = "Starting local runtime";
  std::string side_title = "Command help";
  std::string run_id;
  fs::path directory;
  Focus focus = Focus::Editor;
  Focus menu_origin = Focus::Editor;
  Focus source_origin = Focus::Transcript;
  Panel transcript;
  Panel local_files;
  Panel menu;
  Panel completion;
  Panel source_code;
  Panel source_matches;
  std::optional<Source> source_target;
  std::size_t transcript_bytes = 0;
  tui::Box editor_box;
  tui::Box cursor_box;
  tui::Box files_close_box;
  tui::Box side_close_box;
  tui::Box source_close_box;
  tui::Box source_previous_box;
  tui::Box source_next_box;
  tui::Box batch_cancel_box;
  std::array<tui::Box, 5> toolbar_boxes;
  std::array<tui::Box, 3> side_action_boxes;
  std::vector<display::Line> editor_lines;
  std::vector<tui::Box> editor_rows;
  int editor_text_width = 1;
  bool pasting = false;
  bool pasted_cr = false;
  Panel side;
  std::optional<Reply> side_kind;
  std::vector<std::string> history;
  std::deque<std::pair<std::string, int>> undo;
  std::size_t history_position = 0;
  llvm::StringMap<std::int64_t> commands;
  llvm::StringSet<> open_directories;
  TreeState side_tree;
  std::map<std::int64_t, TreeState> result_trees;
  std::int64_t next_slot = 0;
  bool ready = false;
  bool busy = false;
  bool closing = false;
  bool active_new = false;
  bool wrap = true;
  bool follow = true;
  bool show_hidden = false;
  bool side_requested = false;
  bool menu_visible = false;
  bool files_visible = false;
  bool status_stale = false;
  bool durable_active = false;
  std::int64_t batch_done = 0;
  std::optional<std::int64_t> batch_total;
  std::chrono::steady_clock::time_point started;
  std::optional<double> elapsed;
  std::optional<std::uint64_t> rss;
  std::optional<std::uint64_t> sessions;
};

} // namespace

llvm::Error run_native_workspace(llvm::StringRef file, llvm::StringRef database,
                                 const LoadTarget &load,
                                 const ScriptArguments &arguments) {
  if (!llvm::sys::Process::StandardInIsUserInput() ||
      !llvm::sys::Process::StandardOutIsDisplayed())
    return llvm::createStringError(
        llvm::inconvertibleErrorCode(),
        "workspace UI requires an interactive terminal");
  return WorkspaceScreen(file).run(database, load, arguments);
}

} // namespace ctk::jit
