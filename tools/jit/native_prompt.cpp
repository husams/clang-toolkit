#include "native_prompt.hpp"

#include "platform/repl_cancellation.hpp"
#include "workspace_display.hpp"

#include <array>
#include <iostream>
#include <mutex>

#include <ftxui/component/app.hpp>
#include <ftxui/component/component.hpp>
#include <ftxui/dom/elements.hpp>

#include <llvm/ADT/StringMap.h>
#include <llvm/Support/raw_ostream.h>

namespace ctk::jit {
namespace {

class Prompt {
public:
  explicit Prompt(bool interactive) : interactive(interactive) {}

  std::optional<llvm::json::Object> receive() {
    if (finished)
      return std::nullopt;
    std::string line;
    for (;;) {
      if (interactive) {
        const auto input = read_terminal(line);
        if (input == Input::Cancel) {
          source.clear();
          continue;
        }
        if (input == Input::End)
          return end_of_input();
      } else if (!std::getline(std::cin, line)) {
        return end_of_input();
      }
      if (source.empty()) {
        auto command = llvm::StringRef(line).trim();
        if (command.empty())
          continue;
        if (command.ends_with(";"))
          command = command.drop_back().rtrim();
        if (command == ":quit")
          line = "quit";
      } else {
        source += '\n';
      }
      source += line;
      const auto slot = commands.find(source);
      if (slot == commands.end()) {
        const auto prefix = source + '\n';
        if (llvm::any_of(commands, [&](const auto &item) {
              return item.getKey().starts_with(prefix);
            }))
          continue;
        const auto tokens = workspace_display::tokens(source);
        if (!tokens.empty() && tokens.back().open_literal)
          continue;
      }
      llvm::json::Object request{
          {"slot", slot == commands.end() ? next : slot->second},
          {"history", source}, {"prompt", true}};
      if (slot == commands.end())
        request["source"] = source;
      return request;
    }
  }

  void send(llvm::json::Object reply) {
    if (const auto event = reply.getString("event"))
      write(llvm::outs(), *event + "\n");
    if (const auto error = reply.getString("history_error"))
      write(llvm::errs(), "ctk-jit: " + *error + "\n");
    if (const auto *saved = reply.getArray("history"); saved && interactive) {
      for (const auto &item : *saved)
        if (const auto command = item.getAsString())
          history.push_back(command->str());
    }
    if (reply.getBoolean("incomplete").value_or(false))
      return;
    if (reply.getBoolean("compiled").value_or(false)) {
      if (!slots[next].empty())
        commands.erase(slots[next]);
      slots[next] = source;
      commands.try_emplace(source, next);
      next = (next + 1) % slots.size();
    }
    if (const auto error = reply.getString("error"); error && !error->empty()) {
      write(llvm::errs(), "ctk-jit: " + *error + "\n");
      failed = true;
    }
    if (const auto output = reply.getString("output")) {
      write(llvm::outs(), *output);
      if (reply.getBoolean("history_cleared").value_or(false))
        history.clear();
      else if (interactive)
        history.push_back(source);
      source.clear();
    }
    if (auto exit = reply.getBoolean("exit"))
      finished = *exit;
  }

  bool failed = false;

private:
  enum class Input { Submit, Cancel, End };

  void write(llvm::raw_ostream &stream, const llvm::Twine &text) {
    std::lock_guard lock(output_mutex);
    stream << text;
    stream.flush();
  }

  std::optional<llvm::json::Object> end_of_input() {
    if (!source.empty()) {
      write(llvm::errs(), "ctk-jit: incomplete statement at end of input\n");
      failed = true;
    }
    return std::nullopt;
  }

  Input read_terminal(std::string &line) {
    namespace tui = ftxui;
    line.clear();
    std::string draft;
    auto position = history.size();
    int cursor = 0;
    auto result = Input::End;
    auto app = tui::App::TerminalOutput();
    app.TrackMouse(false);
    app.ForceHandleCtrlC(false);
    tui::InputOption options;
    options.multiline = false;
    options.cursor_position = &cursor;
    auto editor = tui::Input(&line, "", options);
    const auto *label = source.empty() ? "ctk-jit> " : "       > ";
    auto display = tui::Renderer(editor, [&] {
      return tui::hbox({tui::text(label), editor->Render() | tui::flex});
    });
    auto controls = tui::CatchEvent(display, [&](tui::Event event) {
      if (event == tui::Event::Return || event == tui::Event::Special("\r")) {
        result = Input::Submit;
        app.Exit();
        return true;
      }
      if (event == tui::Event::CtrlC || (event == tui::Event::CtrlD && line.empty())) {
        result = event == tui::Event::CtrlC ? Input::Cancel : Input::End;
        app.Exit();
        return true;
      }
      if (source.empty() && event == tui::Event::ArrowUp && position > 0) {
        if (position == history.size())
          draft = line;
        line = history[--position];
      } else if (source.empty() && event == tui::Event::ArrowDown &&
                 position < history.size()) {
        ++position;
        line = position == history.size() ? draft : history[position];
      } else {
        return false;
      }
      cursor = static_cast<int>(line.size());
      return true;
    });
    app.Loop(controls);
    if (result == Input::Cancel)
      write(llvm::outs(), llvm::Twine(label) + "^C\n");
    return result;
  }

  bool interactive;
  std::mutex output_mutex;
  bool finished = false;
  std::string source;
  std::array<std::string, 128> slots;
  std::vector<std::string> history;
  llvm::StringMap<std::int64_t> commands;
  std::int64_t next = 0;
};

} // namespace

llvm::Error run_native_prompt(llvm::StringRef file, llvm::StringRef database,
                              const LoadTarget &load,
                              const ScriptArguments &arguments, bool &failed) {
  const bool interactive = interactive_terminal();
  Prompt prompt(interactive);
  ReplIO io{[&] { return prompt.receive(); },
            [&](llvm::json::Object reply) { prompt.send(std::move(reply)); }};
  const auto run = [&] { return repl_ir(file, database, load, arguments, &io); };
  auto result = interactive ? with_prompt_interrupts(run) : run();
  failed = !interactive && prompt.failed;
  return result;
}

} // namespace ctk::jit
