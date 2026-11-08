#include "native_history.hpp"

#include <array>
#include <cstdlib>
#include <ctime>
#include <fstream>
#include <utility>

#include <llvm/ADT/SmallString.h>
#include <llvm/ADT/StringExtras.h>
#include <llvm/Support/Chrono.h>
#include <llvm/Support/FileSystem.h>
#include <llvm/Support/FormatVariadic.h>
#include <llvm/Support/Path.h>
#include <llvm/Support/RandomNumberGenerator.h>
#include <llvm/Support/raw_ostream.h>

namespace ctk::jit {
namespace {

namespace fs = std::filesystem;
namespace json = llvm::json;

llvm::Error failure(llvm::StringRef action, std::error_code code) {
  return llvm::createStringError(code, "cannot %s history: %s",
                                 action.str().c_str(), code.message().c_str());
}

llvm::Error no_directory() {
  return llvm::createStringError(llvm::inconvertibleErrorCode(),
                                 "set XDG_STATE_HOME or HOME to use history");
}

llvm::Error write(llvm::StringRef path, llvm::StringRef content, bool append) {
  int fd = -1;
  const auto flags = append ? llvm::sys::fs::OF_Append : llvm::sys::fs::OF_None;
  const auto disposition =
      append ? llvm::sys::fs::CD_OpenAlways : llvm::sys::fs::CD_CreateAlways;
  if (const auto error =
          llvm::sys::fs::openFileForWrite(path, fd, disposition, flags, 0600))
    return failure(append ? "append" : "clear", error);
  llvm::raw_fd_ostream output(fd, true);
  output << content;
  output.close();
  if (output.has_error()) {
    const auto error = output.error();
    output.clear_error();
    return failure(append ? "append" : "clear", error);
  }
  return llvm::Error::success();
}

std::string session_id() {
  std::array<unsigned char, 16> bytes{};
  if (llvm::getRandomBytes(bytes.data(), bytes.size()))
    return {};
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  auto text = llvm::toHex(llvm::ArrayRef(bytes), /*LowerCase=*/true);
  for (unsigned index : {20, 16, 12, 8})
    text.insert(index, "-");
  return text;
}

} // namespace

NativeHistory::NativeHistory() : session(session_id()) {
  if (const auto *state = std::getenv("XDG_STATE_HOME")) {
    path = fs::path(state) / "clang_tools/history.jsonl";
  } else {
    llvm::SmallString<256> home;
    if (llvm::sys::path::home_directory(home))
      path =
          fs::path(home.str().str()) / ".local/state/clang_tools/history.jsonl";
  }
}

llvm::Expected<json::Array> NativeHistory::read() const {
  json::Array commands;
  if (path.empty())
    return commands;
  std::ifstream input(path);
  if (!input) {
    std::error_code error;
    if (!fs::exists(path, error) && !error)
      return commands;
    return failure("read",
                   error ? error : std::make_error_code(std::errc::io_error));
  }
  std::string line;
  while (std::getline(input, line)) {
    auto record = json::parse(line);
    if (!record) {
      llvm::consumeError(record.takeError());
      continue;
    }
    if (const auto *object = record->getAsObject())
      if (const auto command = object->getString("command");
          command && !command->trim().empty())
        commands.emplace_back(command->str());
  }
  if (input.bad())
    return failure("read", std::make_error_code(std::errc::io_error));
  return commands;
}

llvm::Error NativeHistory::append(llvm::StringRef command) const {
  if (command.trim().empty())
    return llvm::Error::success();
  if (path.empty())
    return no_directory();
  std::error_code error;
  fs::create_directories(path.parent_path(), error);
  if (error)
    return failure("append", error);
  std::string record;
  std::ifstream existing(path, std::ios::binary | std::ios::ate);
  if (existing && existing.tellg() > 0) {
    existing.seekg(-1, std::ios::end);
    if (existing.get() != '\n')
      record = "\n";
  }
  llvm::raw_string_ostream output(record);
  output << json::Value(json::Object{
                {"timestamp",
                 llvm::formatv("{0:%Y-%m-%dT%H:%M:%SZ}",
                               llvm::sys::toUtcTime(std::time(nullptr)))
                     .str()},
                {"session_id", session},
                {"label", label ? json::Value(*label) : json::Value(nullptr)},
                {"command", command},
            })
         << '\n';
  return write(path.string(), record, true);
}

llvm::Error NativeHistory::action(llvm::StringRef name,
                                  const std::string *text) {
  if (name == "label") {
    label = text ? std::optional(*text) : std::nullopt;
    return llvm::Error::success();
  }
  if (path.empty())
    return no_directory();
  std::error_code error;
  if (name == "clear") {
    fs::create_directories(path.parent_path(), error);
    if (error)
      return failure("clear", error);
    if (auto failed = write(path.string(), "", false))
      return failed;
    cleared = true;
    fs::permissions(path, fs::perms::owner_read | fs::perms::owner_write,
                    error);
    if (error)
      return failure("clear", error);
    return llvm::Error::success();
  }
  if (name == "save" && text) {
    const auto target = fs::absolute(*text, error);
    if (error)
      return failure("save", error);
    fs::create_directories(target.parent_path(), error);
    if (!error)
      fs::copy_file(path, target, fs::copy_options::overwrite_existing, error);
    if (error)
      return failure("save", error);
    return llvm::Error::success();
  }
  return llvm::createStringError(llvm::inconvertibleErrorCode(),
                                 "invalid CTK history action");
}

bool NativeHistory::take_cleared() { return std::exchange(cleared, false); }

} // namespace ctk::jit
