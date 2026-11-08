#include "native_workspace.hpp"
#include "completion.hpp"
#include "grammar/help.hpp"
#include "platform/repl_cancellation.hpp"

#include <algorithm>
#include <array>
#include <condition_variable>
#include <deque>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <string_view>
#include <thread>

#include <clang/ASTMatchers/Dynamic/Parser.h>
#include <clang/ASTMatchers/Dynamic/Registry.h>
#include <ftxui/component/app.hpp>
#include <ftxui/component/component.hpp>
#include <ftxui/dom/elements.hpp>
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
};

struct Panel {
  std::vector<Row> rows;
  std::size_t selected = 0;
  tui::Box bounds;
  std::vector<tui::Box> row_boxes;
  std::size_t column = 0;

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

enum class Focus { Editor, Transcript, Side };

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
        renderer, [&](const auto &event) { return on_event(event); });

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

  void request(Reply purpose, json::Object body) {
    if (!ready)
      return;
    pending.push_back(purpose);
    mailbox.send(std::move(body));
  }

  void append(llvm::StringRef text, std::optional<std::int64_t> preview = {},
              bool markdown = false) {
    llvm::SmallVector<llvm::StringRef, 8> lines;
    text.split(lines, '\n', -1, false);
    for (auto line : lines) {
      constexpr std::size_t limit = 200000;
      line = line.take_back(std::min(line.size(), limit));
      transcript.rows.push_back({line.str(), preview, {}});
      transcript.rows.back().markdown = markdown;
      transcript_bytes += line.size();
      std::size_t remove = 0;
      while (transcript_bytes > limit || transcript.rows.size() - remove > 5000)
        transcript_bytes -= transcript.rows[remove++].text.size();
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
    if (busy || !ready) {
      status = ready ? "A command is running" : "Starting local runtime";
      return;
    }
    if (llvm::StringRef(draft).trim().empty())
      return;
    auto source = std::exchange(draft, {});
    editor_cursor = 0;
    append("ctk-jit> " + source);
    history.push_back(source);
    history_position = history.size();
    const auto [slot, fresh] = commands.try_emplace(source, next_slot);
    if (fresh)
      ++next_slot;
    json::Object body{
        {"slot", slot->second}, {"workspace", true}, {"history", source}};
    if (fresh)
      body["source"] = source;
    active_source = std::move(source);
    active_new = fresh;
    busy = true;
    status = "Running";
    request(Reply::Command, std::move(body));
  }

  void panel_request(Reply kind, llvm::StringRef name) {
    if (side_kind == kind && !side_title.empty()) {
      side_title.clear();
      focus = Focus::Editor;
      return;
    }
    expanded.clear();
    pages = {};
    side_kind = kind;
    side_title = name.str();
    focus = Focus::Side;
    refresh();
  }

  void refresh() {
    if (side_title.empty() || !side_kind)
      return;
    switch (*side_kind) {
    case Reply::Bindings:
      request(Reply::Bindings, projection_request());
      break;
    case Reply::Resources:
      request(Reply::Resources, json::Object{{"inspect", "resources"}});
      break;
    case Reply::Status:
      request(Reply::Status, json::Object{{"inspect", "status"}});
      break;
    case Reply::Preview:
      if (selected_preview) {
        auto query = projection_request();
        query["result"] = *selected_preview;
        request(Reply::Preview, std::move(query));
      }
      break;
    case Reply::Batch:
      if (!run_id.empty())
        request(Reply::Batch,
                json::Object{{"inspect", "batch_status"}, {"run_id", run_id}});
      break;
    case Reply::Command:
    case Reply::Completion:
      break;
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
      const auto purpose = pending.front();
      pending.pop_front();
      if (purpose == Reply::Command) {
        busy = false;
        if (reply.getBoolean("history_cleared").value_or(false)) {
          history.clear();
          history_position = 0;
        }
        const auto error = reply.getString("error").value_or("");
        if (!error.empty()) {
          if (active_new && !reply.getBoolean("compiled").value_or(false))
            commands.erase(active_source);
          status = "Command failed";
          append(error);
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
        if (reply.getBoolean("exit").value_or(false))
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
      } else if (side_kind == purpose) {
        show_panel(purpose, reply.get("value"));
      }
    }
  }

  void batch_progress(const json::Object &progress) {
    run_id = progress.getString("run_id").value_or("").str();
    const auto state = progress.getString("state").value_or("running");
    status = llvm::formatv("Batch {0}: {1} {2}/{3}", run_id, state,
                           progress.getInteger("done").value_or(0),
                           progress.getInteger("total").value_or(0))
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
      const auto path = data->getString("path").value_or(
          data->getString("file").value_or(""));
      if (!path.empty()) {
        const auto line =
            std::max<std::int64_t>(1, data->getInteger("line").value_or(1));
        const auto location = fs::path(path.str());
        rows.push_back(
            {location.filename().string() + ":" + std::to_string(line),
             {},
             Source{location, static_cast<unsigned>(line)}});
      }
      for (const auto &[key, child] : *data)
        source_rows(rows, child);
    } else if (const auto *items = item.getAsArray()) {
      for (const auto &child : *items)
        source_rows(rows, child);
    }
  }

  json::Object projection_request() const {
    json::Array branches;
    for (const auto &name : expanded)
      branches.emplace_back(name.getKey().str());
    return json::Object{{"inspect", "outline"},
                        {"expanded", std::move(branches)},
                        {"pages", json::Value(json::Object(pages))}};
  }

  void projected_rows(std::vector<Row> &rows, const json::Value &value,
                      llvm::StringRef title, std::string path,
                      unsigned depth = 0) {
    const std::string indent(depth * 2, ' ');
    const auto *object = value.getAsObject();
    const auto length = object ? object->getInteger("length") : std::nullopt;
    const auto *children = object ? object->getArray("data") : nullptr;
    const auto type =
        object ? object->getString("kind").value_or("") : llvm::StringRef();
    const auto open = expanded.contains(path);
    if (length && children) {
      rows.push_back(
          {indent + (open ? "▾ " : "▸ ") + title.str() + " = " + label(value),
           {},
           {},
           path});
      if (!open)
        return;
      const auto start = object->getInteger("start").value_or(0);
      if (start > 0)
        rows.push_back(
            {indent + "  ‹ Previous page", {}, {}, path, start / 50 - 1});
      for (std::size_t index = 0; index < children->size(); ++index) {
        const auto &child = (*children)[index];
        if (type == "record") {
          const auto *pair = child.getAsArray();
          if (!pair || pair->size() != 2)
            continue;
          const auto field = (*pair)[0].getAsString().value_or("");
          projected_rows(rows, (*pair)[1], field,
                         path + "[" + as_json(json::Value(field)) + "]",
                         depth + 1);
        } else {
          const auto item = "[" + std::to_string(start + index) + "]";
          projected_rows(rows, child, item, path + item, depth + 1);
        }
      }
      if (start + static_cast<std::int64_t>(children->size()) < *length)
        rows.push_back(
            {indent + "  Next page ›", {}, {}, path, start / 50 + 1});
      return;
    }
    rows.push_back({indent + title.str() + " = " + label(value), {}, {}});
    if (object) {
      const auto begin = rows.size();
      source_rows(rows, value);
      for (auto it = rows.begin() + begin; it != rows.end(); ++it)
        it->text.insert(0, indent + "  ");
    }
  }

  void resource_rows(std::vector<Row> &rows, const json::Object &resources) {
    const auto decode = [&](llvm::StringRef key) {
      const auto *wire = resources.getObject(key);
      return wire ? decode_message(*wire) : json::Value(nullptr);
    };
    const auto quoted = [](llvm::StringRef value) {
      return as_json(json::Value(value));
    };
    const auto files = decode("files");
    const auto *file_list =
        files.getAsObject() ? files.getAsObject()->getArray("files") : nullptr;
    rows.push_back({"Open files · file list", {}, {}});
    if (file_list && !file_list->empty()) {
      for (const auto &entry : *file_list) {
        const auto *file = entry.getAsObject();
        if (!file)
          continue;
        const auto *input = file->getObject("input");
        const auto path = input ? input->getString("filePath").value_or("")
                                : llvm::StringRef();
        const auto lease = file->getString("leaseId").value_or("");
        const auto action =
            lease.empty() ? std::string() : "file close " + quoted(lease);
        const auto name =
            path.empty() ? "File" : fs::path(path.str()).filename().string();
        rows.push_back(
            {"  " + name + (action.empty() ? "" : " · C close"),
             {},
             path.empty() ? std::optional<Source>() : Source{path.str()},
             {},
             {},
             {},
             action});
      }
    } else {
      rows.push_back({"  No open files", {}, {}});
    }
    const auto sessions = decode("sessions");
    const auto *session_list =
        sessions.getAsObject() ? sessions.getAsObject()->getArray("sessions")
                               : nullptr;
    rows.push_back({"Retained sessions · session list", {}, {}});
    if (session_list && !session_list->empty()) {
      for (const auto &entry : *session_list) {
        const auto *session = entry.getAsObject();
        if (!session)
          continue;
        const auto id = session->getString("sessionId").value_or("");
        if (id.empty())
          continue;
        const auto name =
            resources.getString("attach_name").value_or("attached1");
        const auto argument = quoted(id);
        rows.push_back(
            {"  " + id.take_front(12).str() + " · A attach · C close",
             {},
             {},
             {},
             {},
             "session attach " + argument + " into $" + name.str(),
             "session close " + argument});
      }
    } else {
      rows.push_back({"  No retained sessions", {}, {}});
    }
  }

  void durable_progress(const json::Object &wire) {
    const auto data = decode_message(wire);
    const auto *run = data.getAsObject();
    if (!run)
      return;
    run_id = run->getString("runId").value_or("").str();
    const auto state = run->getString("status").value_or("unknown");
    status = "Batch " + run_id + " · " + state.str();
    if (!run_id.empty())
      append(status + " · C cancel");
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
            projected_rows(rows, *bindings->get(name), path, path);
          }
        }
      } else if (purpose == Reply::Resources) {
        if (const auto *resources = value->getAsObject())
          resource_rows(rows, *resources);
      } else if (purpose == Reply::Preview) {
        const auto *object = value->getAsObject();
        const auto type =
            object ? object->getString("kind").value_or("") : llvm::StringRef();
        const auto path = type == "matches"  ? "$Matches"
                          : type == "record" ? "$Dictionary"
                                             : "$List";
        if (type == "matches")
          source_rows(rows, *value);
        projected_rows(rows, *value, path, path);
      } else {
        fields(rows, *value);
      }
    }
    if (rows.empty())
      rows.push_back({"No entries", {}, {}});
    side.replace(std::move(rows));
  }

  void files() {
    side_kind.reset();
    side_title = "Files";
    focus = Focus::Side;
    std::vector<Row> rows;
    std::error_code error;
    if (directory.empty())
      directory = fs::current_path(error);
    if (directory != directory.root_path())
      rows.push_back({"../", {}, Source{directory.parent_path()}});
    for (fs::directory_iterator item(
             directory, fs::directory_options::skip_permission_denied, error),
         end;
         !error && item != end; item.increment(error)) {
      const auto path = item->path();
      const auto filename = path.filename().string();
      if (filename.starts_with(".") && !show_hidden)
        continue;
      std::error_code type_error;
      const bool is_directory = item->is_directory(type_error);
      rows.push_back({filename + (is_directory ? "/" : ""), {}, Source{path}});
    }
    std::ranges::sort(rows, {}, &Row::text);
    side.replace(std::move(rows));
  }

  void open_source(const Source &target) {
    std::error_code error;
    if (fs::is_directory(target.path, error)) {
      directory = target.path;
      files();
      return;
    }
    std::ifstream source(target.path);
    if (!source) {
      status = "Cannot open " + target.path.string();
      return;
    }
    side_kind.reset();
    side_title = target.path.filename().string();
    focus = Focus::Side;
    std::vector<Row> lines;
    std::string line;
    for (unsigned i = 1; std::getline(source, line); ++i)
      lines.push_back({std::to_string(i) + "  " + line, {}, {}});
    side.replace(std::move(lines));
    side.selected = 0;
    side.move(static_cast<int>(target.line) - 1);
  }

  void help() {
    if (side_title == "Workspace help") {
      side_title.clear();
      focus = Focus::Editor;
      return;
    }
    side_kind.reset();
    side_title = "Workspace help";
    std::vector<Row> rows{
        {"Enter executes CTK. Alt+Enter inserts a newline.", {}, {}},
        {"F3 files  F5 refresh  F6 focus  F7 bindings", {}, {}},
        {"F8 resources  F9 runtime  F10 quit", {}, {}},
        {"Enter on a result opens its preview. O opens its source.", {}, {}},
        {"Ctrl+C cancels an active command or clears the draft.", {}, {}},
    };
    const auto reference = native_help("");
    llvm::SmallVector<llvm::StringRef, 64> lines;
    llvm::StringRef(reference.markdown).split(lines, '\n');
    for (const auto line : lines) {
      rows.push_back({line.str(), {}, {}});
      rows.back().markdown = true;
    }
    side.replace(std::move(rows));
    side.selected = 0;
    focus = Focus::Side;
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

  void insert_newline() {
    const auto at = static_cast<std::size_t>(editor_cursor);
    const auto before = llvm::StringRef(draft).take_front(at);
    const auto newline = before.rfind('\n');
    const auto line = newline == llvm::StringRef::npos
                          ? before
                          : before.drop_front(newline + 1);
    const auto count = line.find_first_not_of(" \t");
    auto indentation =
        line.take_front(count == llvm::StringRef::npos ? line.size() : count)
            .str();
    if (llvm::StringRef(before).rtrim().ends_with("{") ||
        before.rtrim().ends_with("[") || before.rtrim().ends_with("(") ||
        before.rtrim().ends_with(" do"))
      indentation += "    ";
    draft.insert(at, "\n" + indentation);
    editor_cursor += static_cast<int>(indentation.size()) + 1;
  }

  bool incomplete() const {
    auto text = llvm::StringRef(draft).rtrim();
    if (text.ends_with("|") || text.ends_with("=") || text.ends_with(" do"))
      return true;
    std::vector<char> delimiters;
    char quote = 0;
    bool comment = false;
    for (std::size_t index = 0; index < text.size(); ++index) {
      const auto ch = text[index];
      if (comment) {
        comment = ch != '\n';
      } else if (quote) {
        if (ch == '\\')
          ++index;
        else if (ch == quote)
          quote = 0;
      } else if (ch == '\'' || ch == '"' || ch == '`') {
        quote = ch;
      } else if (ch == '#' || text.substr(index, 2) == "//") {
        comment = true;
      } else if (ch == '(' || ch == '{' || ch == '[') {
        delimiters.push_back(ch);
      } else if (ch == ')' || ch == '}' || ch == ']') {
        if (!delimiters.empty())
          delimiters.pop_back();
      }
    }
    return quote || !delimiters.empty();
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
    side_kind.reset();
    side_title = "Completions";
    completion_open = true;
    focus = Focus::Side;
    side.replace(std::move(results));
    side.selected = 0;
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

  void complete() {
    if (completion_open) {
      side.move(1);
      return;
    }
    if (completion_query || complete_presence())
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
    if (const auto *row = side.current()) {
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
    completion_open = false;
    side_title.clear();
    focus = Focus::Editor;
  }

  bool smart_pair(const tui::Event &event) {
    if (!event.is_character())
      return false;
    const auto text = event.character();
    if (text.size() != 1)
      return false;
    const auto ch = text.front();
    const auto at = static_cast<std::size_t>(editor_cursor);
    if (at < draft.size() && ch == draft[at] &&
        std::string_view(")]}'\"").contains(ch)) {
      ++editor_cursor;
      return true;
    }
    constexpr std::string_view open = "([{'\"";
    constexpr std::string_view close = ")]}'\"";
    const auto pair = open.find(ch);
    if (pair == std::string_view::npos)
      return false;
    draft.insert(at, {ch, close[pair]});
    ++editor_cursor;
    return true;
  }

  void start_search() {
    searching_transcript = focus == Focus::Transcript;
    saved_draft = draft;
    set_draft({});
    focus = Focus::Editor;
    searching = true;
    status = searching_transcript ? "Search transcript" : "Search history";
  }

  void accept_search() {
    const auto query = draft;
    set_draft(std::move(saved_draft));
    searching = false;
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

  static const auto &toolbar_actions() {
    static const std::array actions{
        std::pair{"Actions", tui::Event::F2},
        std::pair{"Help", tui::Event::F4},
        std::pair{"Outline", tui::Event::F7},
        std::pair{"Resources", tui::Event::F8},
        std::pair{"Runtime", tui::Event::F9},
        std::pair{"×", tui::Event::Escape},
    };
    return actions;
  }

  bool on_mouse(const tui::Mouse &mouse) {
    if (mouse.button == tui::Mouse::Left &&
        mouse.motion == tui::Mouse::Pressed) {
      for (std::size_t i = 0; i < toolbar_boxes.size(); ++i)
        if (toolbar_boxes[i].Contain(mouse.x, mouse.y))
          return on_event(toolbar_actions()[i].second);
    }
    Panel *panel = nullptr;
    Focus target = Focus::Editor;
    if (!side_title.empty() && side.bounds.Contain(mouse.x, mouse.y)) {
      panel = &side;
      target = Focus::Side;
    } else if (transcript.bounds.Contain(mouse.x, mouse.y)) {
      panel = &transcript;
      target = Focus::Transcript;
    }
    if (!panel) {
      if (editor_box.Contain(mouse.x, mouse.y))
        focus = Focus::Editor;
      return false;
    }
    if (mouse.button == tui::Mouse::WheelUp ||
        mouse.button == tui::Mouse::WheelDown) {
      focus = target;
      panel->move(mouse.button == tui::Mouse::WheelUp ? -3 : 3);
      if (target == Focus::Transcript)
        follow = false;
      return true;
    }
    if (mouse.button != tui::Mouse::Left || mouse.motion != tui::Mouse::Pressed)
      return false;
    focus = target;
    for (std::size_t i = 0; i < panel->row_boxes.size(); ++i) {
      if (!panel->row_boxes[i].Contain(mouse.x, mouse.y))
        continue;
      const auto selected = panel->selected == i;
      panel->selected = i;
      if (selected)
        return on_event(tui::Event::Return);
      break;
    }
    return true;
  }

  bool on_event(tui::Event event) {
    using tui::Event;
    if (event == Event::Custom) {
      drain();
      return true;
    }
    if (event == Event::Special("\x1b[200~")) {
      pasting = true;
      return true;
    }
    if (event == Event::Special("\x1b[201~")) {
      pasting = false;
      return true;
    }
    if (pasting) {
      if (event == Event::Return)
        insert_draft("\n");
      else if (event == Event::Tab)
        insert_draft("\t");
      else if (event.is_character())
        insert_draft(event.character());
      return true;
    }
    if (event.is_mouse())
      return on_mouse(event.mouse());
    if (event == Event::CtrlR) {
      if (!searching)
        start_search();
    } else if (searching) {
      if (event == Event::Return)
        accept_search();
      else if (event == Event::Escape || event == Event::CtrlC) {
        set_draft(std::move(saved_draft));
        searching = false;
        status = "Ready";
      } else {
        return false;
      }
    } else if (event == Event::Tab &&
               (focus == Focus::Editor || completion_open)) {
      complete();
    } else if (completion_open && event == Event::Return) {
      accept_completion();
    } else if (event == Event::F1 || event == Event::F4) {
      help();
    } else if (event == Event::F2) {
      side_kind.reset();
      side_title = "Workspace actions";
      std::vector<Row> actions;
      for (const auto &[key, text] : {
               std::pair{'r', "Run command"},
               std::pair{'f', "Files"},
               std::pair{'h', "Toggle hidden files"},
               std::pair{'l', "Follow latest output"},
               std::pair{'s', "Search transcript"},
               std::pair{'w', "Toggle transcript wrapping"},
               std::pair{'x', "Clear transcript"},
               std::pair{'c', "Cancel the current batch"},
               std::pair{'q', "Quit"},
           }) {
        actions.push_back({text, {}, {}});
        actions.back().action = key;
      }
      side.replace(std::move(actions));
      side.selected = 0;
      focus = Focus::Side;
    } else if (event == Event::F3) {
      if (side_title == "Files") {
        side_title.clear();
        focus = Focus::Editor;
      } else {
        files();
      }
    } else if (event == Event::F5) {
      if (side_title == "Files")
        files();
      else
        refresh();
    } else if (event == Event::F6 || event == Event::Special("\x1b[29~") ||
               event == Event::Special("\x1b[17;2~")) {
      const bool reverse = event != Event::F6;
      if (!reverse) {
        focus = focus == Focus::Editor ? Focus::Transcript
                : focus == Focus::Transcript && !side_title.empty()
                    ? Focus::Side
                    : Focus::Editor;
      } else {
        focus = focus == Focus::Editor && !side_title.empty() ? Focus::Side
                : focus == Focus::Side || focus == Focus::Editor
                    ? Focus::Transcript
                    : Focus::Editor;
      }
    } else if (event == Event::F7) {
      panel_request(Reply::Bindings, "Bindings");
    } else if (event == Event::F8) {
      panel_request(Reply::Resources, "Resources");
    } else if (event == Event::F9) {
      panel_request(Reply::Status, "Runtime status");
    } else if (event == Event::F10 ||
               (event == Event::CtrlD && draft.empty())) {
      app.Exit();
    } else if (event == Event::Escape) {
      completion_open = false;
      side_title.clear();
      focus = Focus::Editor;
    } else if (event == Event::CtrlC) {
      if (busy) {
        request_repl_cancellation();
        status = "Cancellation requested";
      } else {
        set_draft({});
      }
    } else if (focus != Focus::Editor) {
      auto &panel = focus == Focus::Transcript ? transcript : side;
      if (event == Event::ArrowUp || event == Event::PageUp) {
        panel.move(event == Event::ArrowUp ? -1 : -10);
        if (focus == Focus::Transcript)
          follow = false;
      } else if (event == Event::ArrowDown || event == Event::PageDown) {
        panel.move(event == Event::ArrowDown ? 1 : 10);
      } else if (event == Event::ArrowLeftCtrl ||
                 event == Event::ArrowRightCtrl) {
        panel.column = event == Event::ArrowLeftCtrl
                           ? (panel.column >= 8 ? panel.column - 8 : 0)
                           : panel.column + 8;
      } else if (event == Event::Special("\x1b[1;5F")) {
        follow = true;
        transcript.move(static_cast<int>(transcript.rows.size()));
      } else if (event == Event::Return || event == Event::ArrowRight ||
                 event == Event::Character('o')) {
        if (const auto *row = panel.current()) {
          if (row->action) {
            return on_event(Event::Character(row->action));
          } else if (row->source) {
            std::error_code error;
            if (side_title == "Files" && event == Event::Return &&
                fs::is_regular_file(row->source->path, error)) {
              set_draft("parse " +
                        as_json(json::Value(row->source->path.string())));
              side_title.clear();
              focus = Focus::Editor;
            } else {
              open_source(*row->source);
            }
          } else if (row->preview) {
            selected_preview = row->preview;
            side_kind = Reply::Preview;
            side_title = "Result preview";
            focus = Focus::Side;
            expanded.clear();
            pages = {};
            for (const auto *path :
                 {"$Matches", "$Matches[0]", "$List", "$Dictionary"})
              expanded.insert(path);
            refresh();
          } else if (row->page) {
            pages[row->branch] = *row->page;
            refresh();
          } else if (!row->branch.empty()) {
            if (!expanded.erase(row->branch))
              expanded.insert(row->branch);
            refresh();
          }
        }
      } else if (event == Event::ArrowLeft) {
        if (const auto *row = panel.current();
            row && expanded.erase(row->branch))
          refresh();
      } else if (event == Event::Character('a')) {
        if (const auto *row = panel.current(); row && !row->attach.empty()) {
          set_draft(row->attach);
          focus = Focus::Editor;
        }
      } else if (event == Event::Character('w')) {
        wrap = !wrap;
      } else if (event == Event::Character('l')) {
        follow = true;
        transcript.move(static_cast<int>(transcript.rows.size()));
      } else if (event == Event::Character('q') &&
                 side_title == "Workspace actions") {
        app.Exit();
      } else if (event == Event::Character('s') &&
                 side_title == "Workspace actions") {
        side_title.clear();
        focus = Focus::Transcript;
        start_search();
      } else if (event == Event::Character('f') &&
                 side_title == "Workspace actions") {
        files();
      } else if (event == Event::Character('r') &&
                 side_title == "Workspace actions") {
        side_title.clear();
        focus = Focus::Editor;
        submit();
      } else if (event == Event::Character('x') &&
                 side_title == "Workspace actions") {
        transcript.replace({});
        transcript_bytes = 0;
      } else if (event == Event::Character('h')) {
        show_hidden = !show_hidden;
        if (side_title == "Files")
          files();
      } else if (event == Event::Character('c')) {
        if (busy) {
          request_repl_cancellation();
        } else if (const auto *row = panel.current();
                   row && !row->close.empty()) {
          set_draft(row->close);
          focus = Focus::Editor;
        } else if (!run_id.empty())
          request(Reply::Batch, json::Object{{"inspect", "batch_cancel"},
                                             {"run_id", run_id}});
      }
    } else if (event == Event::Return) {
      if (static_cast<std::size_t>(editor_cursor) < draft.size() ||
          incomplete())
        insert_newline();
      else
        submit();
    } else if (event == Event::Special("\x1b\r") ||
               event == Event::Special("\x1b\n") ||
               event == Event::Special("\x1b[13;2u") ||
               event == Event::Special("\x1b[13;5u") ||
               event == Event::Special("\x1b[27;5;13~")) {
      insert_newline();
    } else if (event == Event::ArrowUp && history_position > 0 &&
               !llvm::StringRef(draft)
                    .take_front(editor_cursor)
                    .contains('\n')) {
      set_draft(history[--history_position]);
    } else if (event == Event::ArrowDown && history_position < history.size() &&
               !llvm::StringRef(draft)
                    .drop_front(editor_cursor)
                    .contains('\n')) {
      ++history_position;
      set_draft(history_position == history.size() ? std::string()
                                                   : history[history_position]);
    } else if (smart_pair(event)) {
      return true;
    } else {
      return false;
    }
    return true;
  }

  tui::Element render_panel(Panel &panel, bool focused, bool wrapping) {
    tui::Elements rows;
    panel.row_boxes.resize(panel.rows.size());
    bool code = false;
    for (std::size_t i = 0; i < panel.rows.size(); ++i) {
      const auto &row = panel.rows[i];
      auto text = llvm::StringRef(row.text);
      auto offset = std::min(panel.column, text.size());
      while (offset < text.size() &&
             (static_cast<unsigned char>(text[offset]) & 0xc0) == 0x80)
        ++offset;
      text = text.drop_front(offset);
      auto element = wrapping && panel.column == 0 ? tui::paragraph(text.str())
                                                   : tui::text(text.str());
      if (row.markdown) {
        if (text.starts_with("```")) {
          code = !code;
          element = tui::text("");
        } else if (code) {
          element = tui::text(text.str()) | tui::bgcolor(tui::Color::Grey15);
        } else if (text.starts_with("#")) {
          element = tui::paragraph(text.ltrim("# ").str()) | tui::bold |
                    tui::color(tui::Color::CyanLight);
        }
      } else if (text.starts_with("ctk-jit>")) {
        element = element | tui::color(tui::Color::CyanLight);
      }
      if (i == panel.selected) {
        if (focused)
          element = element | tui::inverted;
        element = element | tui::focus;
      }
      rows.push_back(std::move(element) | tui::reflect(panel.row_boxes[i]));
    }
    return tui::vbox(std::move(rows)) | tui::vscroll_indicator | tui::yframe |
           tui::reflect(panel.bounds) | tui::flex;
  }

  tui::Element render(const tui::Component &editor) {
    auto left = tui::vbox({
                    tui::text("CTK editor") | tui::bold,
                    editor->Render() | tui::yframe |
                        tui::size(tui::HEIGHT, tui::LESS_THAN, 8) |
                        tui::reflect(editor_box),
                    tui::separator(),
                    tui::text("Transcript") | tui::bold,
                    render_panel(transcript, focus == Focus::Transcript, wrap),
                }) |
                tui::flex;
    if (!side_title.empty()) {
      auto panel =
          tui::vbox({tui::text(side_title) | tui::bold, tui::separator(),
                     render_panel(side, focus == Focus::Side, true)}) |
          tui::flex;
      if (app.dimx() > 75)
        left =
            tui::hbox({std::move(left), tui::separator(), std::move(panel)}) |
            tui::flex;
      else if (focus == Focus::Side)
        left = std::move(panel);
    }
    tui::Elements toolbar{tui::text("CTK workspace · LLVM IR") | tui::bold,
                          tui::filler()};
    for (std::size_t i = 0; i < toolbar_actions().size(); ++i) {
      if (i + 1 == toolbar_actions().size() && side_title.empty()) {
        toolbar_boxes[i] = tui::Box{1, 0, 1, 0};
        continue;
      }
      toolbar.push_back(
          tui::text(std::string(" ") + toolbar_actions()[i].first + " ") |
          tui::reflect(toolbar_boxes[i]));
    }
    return tui::vbox(
        {tui::hbox(std::move(toolbar)), tui::separator(), std::move(left),
         tui::separator(), tui::text(status),
         tui::text("F1 Help  F2 Menu  F3 Files  F6 Focus  F7 Bindings  F8 "
                   "Resources  F9 Status  F10 Quit")});
  }

  std::string file;
  tui::App app;
  Mailbox mailbox;
  std::deque<Reply> pending;
  std::string draft;
  int editor_cursor = 0;
  std::size_t completion_begin = 0;
  std::size_t completion_end = 0;
  bool completion_open = false;
  std::optional<CompletionQuery> completion_query;
  bool searching = false;
  bool searching_transcript = false;
  std::string saved_draft;
  std::string active_source;
  std::string status = "Starting local runtime";
  std::string side_title;
  std::string run_id;
  fs::path directory;
  Focus focus = Focus::Editor;
  Panel transcript;
  std::size_t transcript_bytes = 0;
  tui::Box editor_box;
  std::array<tui::Box, 6> toolbar_boxes;
  bool pasting = false;
  Panel side;
  std::optional<Reply> side_kind;
  std::optional<std::int64_t> selected_preview;
  std::vector<std::string> history;
  std::size_t history_position = 0;
  llvm::StringMap<std::int64_t> commands;
  llvm::StringSet<> expanded;
  json::Object pages;
  std::int64_t next_slot = 0;
  bool ready = false;
  bool busy = false;
  bool active_new = false;
  bool wrap = true;
  bool follow = true;
  bool show_hidden = false;
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
