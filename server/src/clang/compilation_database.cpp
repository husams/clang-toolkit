#include "ctk/clang/compilation_database.hpp"

#include <clang/Tooling/ArgumentsAdjusters.h>
#include <clang/Tooling/JSONCompilationDatabase.h>
#include <llvm/Support/JSON.h>
#include <llvm/Support/raw_ostream.h>
#include <sqlite3.h>

#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <memory>
#include <mutex>
#include <optional>
#include <stdexcept>

namespace ctk::clang_layer {
namespace {
namespace fs = std::filesystem;

fs::path absolute(const fs::path &path, const fs::path &directory) {
  return fs::weakly_canonical(path.is_absolute() ? path : directory / path);
}

std::optional<fs::path> discover(const FileInput &input, const fs::path &source,
                                 const fs::path &working) {
  if (!input.compilation_database.empty()) {
    auto path = absolute(input.compilation_database, working);
    if (fs::is_directory(path))
      path /= "compile_commands.json";
    if (!fs::is_regular_file(path))
      throw std::invalid_argument("compilation database not found: " +
                                  path.string());
    return path;
  }
  for (auto start : {working, source.parent_path()}) {
    for (auto directory = start; !directory.empty();) {
      for (const auto *suffix :
           {"compile_commands.json", "build/compile_commands.json"}) {
        auto candidate = directory / suffix;
        if (fs::is_regular_file(candidate))
          return fs::weakly_canonical(candidate);
      }
      auto parent = directory.parent_path();
      if (parent == directory)
        break;
      directory = std::move(parent);
    }
  }
  return std::nullopt;
}

fs::path index_path() {
  fs::path root;
  if (const auto *value = std::getenv("CTK_STORAGE_ROOT"); value && *value)
    root = value;
  else if (const auto *value = std::getenv("XDG_CACHE_HOME"); value && *value)
    root = fs::path(value) / "clang-toolkit" / "storage";
  else if (const auto *value = std::getenv("HOME"); value && *value)
    root = fs::path(value) / ".cache" / "clang-toolkit" / "storage";
  else
    root = fs::temp_directory_path() / "clang-toolkit-storage";
  fs::create_directories(root);
  return root / "compile_commands.sqlite3";
}

void check(sqlite3 *database, int status) {
  if (status != SQLITE_OK && status != SQLITE_DONE && status != SQLITE_ROW)
    throw std::runtime_error("compilation index: " +
                             std::string(sqlite3_errmsg(database)));
}

class Statement {
public:
  Statement(sqlite3 *database, const char *sql) : database_(database) {
    sqlite3_stmt *statement = nullptr;
    const auto status =
        sqlite3_prepare_v2(database, sql, -1, &statement, nullptr);
    statement_.reset(statement);
    check(database, status);
  }
  void bind(int index, const std::string &value) {
    check(database_,
          sqlite3_bind_text(statement_.get(), index, value.data(),
                            static_cast<int>(value.size()), SQLITE_TRANSIENT));
  }
  bool step() {
    auto status = sqlite3_step(statement_.get());
    check(database_, status);
    return status == SQLITE_ROW;
  }
  std::string text(int column) const {
    const auto *value = sqlite3_column_text(statement_.get(), column);
    return value ? reinterpret_cast<const char *>(value) : "";
  }

private:
  sqlite3 *database_;
  std::unique_ptr<sqlite3_stmt, decltype(&sqlite3_finalize)> statement_{
      nullptr, sqlite3_finalize};
};

std::string signature(const fs::path &path) {
  return std::to_string(std::chrono::duration_cast<std::chrono::nanoseconds>(
                            fs::last_write_time(path).time_since_epoch())
                            .count()) +
         ":" + std::to_string(fs::file_size(path));
}

class CompilationIndex {
public:
  CompilationIndex() {
    sqlite3 *database = nullptr;
    auto status = sqlite3_open_v2(index_path().string().c_str(), &database,
                                  SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE |
                                      SQLITE_OPEN_FULLMUTEX,
                                  nullptr);
    database_.reset(database);
    check(database, status);
    check(database, sqlite3_busy_timeout(database, 5000));
    execute("PRAGMA journal_mode=WAL");
    execute("CREATE TABLE IF NOT EXISTS compilation_sources (path TEXT PRIMARY "
            "KEY, signature TEXT NOT NULL)");
    execute("CREATE TABLE IF NOT EXISTS compilation_commands (database_path "
            "TEXT NOT NULL, file TEXT NOT NULL, ordinal INTEGER NOT NULL, "
            "directory TEXT NOT NULL, arguments TEXT NOT NULL, PRIMARY "
            "KEY(database_path,file,ordinal))");
  }

  std::optional<FileInput> lookup(const fs::path &path,
                                  const fs::path &source) {
    std::lock_guard guard(mutex_);
    const auto stamp = signature(path);
    bool stale = false;
    {
      Statement previous(
          database_.get(),
          "SELECT signature FROM compilation_sources WHERE path=?");
      previous.bind(1, path.string());
      stale = !previous.step() || previous.text(0) != stamp;
    }
    if (stale)
      refresh(path);
    Statement command(
        database_.get(),
        "SELECT directory,arguments FROM compilation_commands WHERE "
        "database_path=? AND file=? ORDER BY ordinal LIMIT 1");
    command.bind(1, path.string());
    command.bind(2, source.string());
    if (!command.step())
      return std::nullopt;
    FileInput result{source.string(), {}, command.text(0)};
    auto parsed = llvm::json::parse(command.text(1));
    if (!parsed)
      throw std::runtime_error("invalid cached compilation command: " +
                               llvm::toString(parsed.takeError()));
    auto *arguments = parsed->getAsArray();
    if (!arguments)
      throw std::runtime_error("invalid cached compilation arguments");
    for (const auto &argument : *arguments) {
      auto text = argument.getAsString();
      if (!text)
        throw std::runtime_error("invalid cached compiler argument");
      result.compile_arguments.push_back(text->str());
    }
    return result;
  }

private:
  void execute(const char *sql) {
    check(database_.get(),
          sqlite3_exec(database_.get(), sql, nullptr, nullptr, nullptr));
  }
  void refresh(const fs::path &path) {
    // Parse before publishing: malformed/replaced JSON never overwrites a good
    // generation, nor permits serving its stale flags on this request.
    const auto before = signature(path);
    std::string error;
    auto native = clang::tooling::JSONCompilationDatabase::loadFromFile(
        path.string(), error,
        clang::tooling::JSONCommandLineSyntax::AutoDetect);
    if (!native)
      throw std::invalid_argument("cannot load compilation database " +
                                  path.string() + ": " + error);
    auto commands = native->getAllCompileCommands();
    if (signature(path) != before)
      throw std::invalid_argument(
          "compilation database changed during import; retry the request");
    execute("BEGIN IMMEDIATE");
    try {
      Statement remove(
          database_.get(),
          "DELETE FROM compilation_commands WHERE database_path=?");
      remove.bind(1, path.string());
      remove.step();
      std::size_t ordinal = 0;
      for (const auto &command : commands) {
        if (command.CommandLine.empty())
          throw std::invalid_argument("empty compilation command in " +
                                      path.string());
        const auto directory = absolute(command.Directory, path.parent_path());
        const auto source = absolute(command.Filename, directory);
        // Store native argv, including response-file references; expansion is
        // request-local so changes to response files are captured by the AST.
        llvm::json::Array arguments;
        for (const auto &argument : command.CommandLine)
          arguments.push_back(argument);
        std::string serialized;
        llvm::raw_string_ostream stream(serialized);
        stream << llvm::json::Value(std::move(arguments));
        Statement insert(database_.get(),
                         "INSERT INTO compilation_commands VALUES(?,?,?,?,?)");
        insert.bind(1, path.string());
        insert.bind(2, source.string());
        insert.bind(3, std::to_string(ordinal++));
        insert.bind(4, directory.string());
        insert.bind(5, serialized);
        insert.step();
      }
      if (signature(path) != before)
        throw std::invalid_argument(
            "compilation database changed during import; retry the request");
      Statement publish(
          database_.get(),
          "INSERT OR REPLACE INTO compilation_sources VALUES(?,?)");
      publish.bind(1, path.string());
      publish.bind(2, before);
      publish.step();
      execute("COMMIT");
    } catch (...) {
      sqlite3_exec(database_.get(), "ROLLBACK", nullptr, nullptr, nullptr);
      throw;
    }
  }
  std::mutex mutex_;
  std::unique_ptr<sqlite3, decltype(&sqlite3_close)> database_{nullptr,
                                                               sqlite3_close};
};

} // namespace

FileInput resolve_compilation_command(const FileInput &input) {
  auto working = fs::absolute(input.working_directory.empty()
                                  ? fs::current_path()
                                  : fs::path(input.working_directory));
  const auto source = absolute(input.path, working);
  auto database = discover(input, source, working);
  if (!database)
    return input;
  static CompilationIndex index;
  auto command = index.lookup(*database, source);
  if (!command) {
    if (!input.compilation_database.empty())
      throw std::invalid_argument(
          "compile command not found for source file: " + source.string() +
          " in " + database->string());
    return input;
  }
  auto raw = std::move(command->compile_arguments);
  command->compile_arguments.clear();
  // The AST builder expands response files on its private captured filesystem.
  // Remove the driver, source and build output; append request overrides last.
  std::size_t first = 1;
  const auto driver = fs::path(raw.front()).filename().string();
  if (driver == "ccache" || driver == "sccache" || driver == "distcc")
    first = 2;
  for (std::size_t i = first; i < raw.size(); ++i)
    command->compile_arguments.push_back(raw[i]);
  command->compile_arguments.insert(command->compile_arguments.end(),
                                    input.compile_arguments.begin(),
                                    input.compile_arguments.end());
  command->compilation_database = database->string();
  return *command;
}
} // namespace ctk::clang_layer
