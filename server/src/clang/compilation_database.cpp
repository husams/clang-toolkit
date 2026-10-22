#include "ctk/clang/compilation_database.hpp"

#include <clang/Tooling/ArgumentsAdjusters.h>
#include <clang/Tooling/JSONCompilationDatabase.h>
#include <llvm/Support/JSON.h>
#include <llvm/Support/MemoryBuffer.h>
#include <llvm/Support/raw_ostream.h>
#include <sqlite3.h>

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <memory>
#include <mutex>
#include <optional>
#include <stdexcept>
#include <unordered_map>

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
           {"compile_commands.json", "build/compile_commands.json",
            "build/dev/compile_commands.json",
            "build/release/compile_commands.json"}) {
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
  // Reimport older cache generations once to populate the directory donors.
  return "directory-donors-v1:" +
         std::to_string(std::chrono::duration_cast<std::chrono::nanoseconds>(
                            fs::last_write_time(path).time_since_epoch())
                            .count()) +
         ":" + std::to_string(fs::file_size(path));
}

// Keep exact lookups in SQLite. Clang's inference index needs only the file
// names; fetch the chosen TU's first command without re-reading the JSON file.
class IndexedCompilationDatabase final
    : public clang::tooling::CompilationDatabase {
public:
  IndexedCompilationDatabase(sqlite3 *database, std::string path)
      : database_(database), path_(std::move(path)) {}

  std::vector<std::string> getAllFiles() const override {
    Statement files(database_,
                    "SELECT DISTINCT file FROM compilation_commands WHERE "
                    "database_path=? ORDER BY file");
    files.bind(1, path_);
    std::vector<std::string> result;
    while (files.step())
      result.push_back(files.text(0));
    return result;
  }

  std::vector<clang::tooling::CompileCommand>
  getCompileCommands(llvm::StringRef source) const override {
    Statement command(
        database_, "SELECT directory,arguments FROM compilation_commands "
                   "WHERE database_path=? AND file=? ORDER BY ordinal LIMIT 1");
    command.bind(1, path_);
    command.bind(2, source.str());
    if (!command.step())
      return {};
    auto parsed = llvm::json::parse(command.text(1));
    if (!parsed)
      throw std::runtime_error("invalid cached compilation command: " +
                               llvm::toString(parsed.takeError()));
    auto *arguments = parsed->getAsArray();
    if (!arguments)
      throw std::runtime_error("invalid cached compilation arguments");
    std::vector<std::string> argv;
    for (const auto &argument : *arguments) {
      auto text = argument.getAsString();
      if (!text)
        throw std::runtime_error("invalid cached compiler argument");
      argv.push_back(text->str());
    }
    return {clang::tooling::CompileCommand(command.text(0), source,
                                           std::move(argv), "")};
  }

  std::optional<std::string> first_sibling(const fs::path &source) const {
    Statement command(database_,
                      "SELECT file FROM compilation_directory_donors "
                      "WHERE database_path=? AND source_directory=?");
    command.bind(1, path_);
    command.bind(2, source.parent_path().string());
    if (command.step())
      return command.text(0);
    return std::nullopt;
  }

private:
  sqlite3 *database_;
  std::string path_;
};

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
    execute("CREATE TABLE IF NOT EXISTS compilation_directory_donors "
            "(database_path TEXT NOT NULL, source_directory TEXT NOT NULL, "
            "file TEXT NOT NULL, PRIMARY KEY(database_path,source_directory))");
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
    IndexedCompilationDatabase exact(database_.get(), path.string());
    auto commands = exact.getCompileCommands(source.string());
    if (commands.empty()) {
      if (auto sibling = exact.first_sibling(source)) {
        // Transfer only the first command in this source directory. Expand
        // response files before replacing the donor's input/output operands.
        auto expanded = clang::tooling::inferTargetAndDriverMode(
            clang::tooling::expandResponseFiles(
                std::make_unique<IndexedCompilationDatabase>(
                    database_.get(), path.string()),
                llvm::IntrusiveRefCntPtr<llvm::vfs::FileSystem>(
                    llvm::vfs::createPhysicalFileSystem().release())));
        commands = expanded->getCompileCommands(*sibling);
        if (!commands.empty())
          commands.front() = clang::tooling::transferCompileCommand(
              std::move(commands.front()), source.string());
      }
    }
    if (commands.empty()) {
      auto &inferred = inferred_[path.string()];
      if (!inferred.database || inferred.signature != stamp) {
        // This is the JSON database plugin used by clang-query: expand response
        // files before transferring -x/-std and replacing input/output
        // operands. The filesystem has private CWD state, and expansion runs on
        // each lookup so response-file changes also change the effective
        // profile.
        inferred.database = clang::tooling::inferTargetAndDriverMode(
            clang::tooling::inferMissingCompileCommands(
                clang::tooling::expandResponseFiles(
                    std::make_unique<IndexedCompilationDatabase>(
                        database_.get(), path.string()),
                    llvm::IntrusiveRefCntPtr<llvm::vfs::FileSystem>(
                        llvm::vfs::createPhysicalFileSystem().release()))));
        inferred.signature = stamp;
      }
      commands = inferred.database->getCompileCommands(source.string());
    }
    if (commands.empty())
      return std::nullopt;
    auto &command = commands.front();
    return FileInput{source.string(), std::move(command.CommandLine),
                     std::move(command.Directory)};
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
      Statement remove_donors(
          database_.get(),
          "DELETE FROM compilation_directory_donors WHERE database_path=?");
      remove_donors.bind(1, path.string());
      remove_donors.step();
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
        // The first command in database order owns this source directory.
        Statement donor(
            database_.get(),
            "INSERT OR IGNORE INTO compilation_directory_donors VALUES(?,?,?)");
        donor.bind(1, path.string());
        donor.bind(2, source.parent_path().string());
        donor.bind(3, source.string());
        donor.step();
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
      inferred_.erase(path.string());
    } catch (...) {
      sqlite3_exec(database_.get(), "ROLLBACK", nullptr, nullptr, nullptr);
      throw;
    }
  }
  std::mutex mutex_;
  std::unique_ptr<sqlite3, decltype(&sqlite3_close)> database_{nullptr,
                                                               sqlite3_close};
  struct InferredDatabase {
    std::string signature;
    std::unique_ptr<clang::tooling::CompilationDatabase> database;
  };
  std::unordered_map<std::string, InferredDatabase> inferred_;
};

} // namespace

FileInput resolve_compilation_command(const FileInput &input) {
  if (input.compilation_profile_frozen)
    return input;
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
  // Exact commands retain response files for the AST builder's captured
  // filesystem; inferred commands have already expanded them. Remove the
  // driver here; the builder strips source/output operands. Append overrides
  // last, before any input separator.
  std::size_t first = 1;
  const auto driver = fs::path(raw.front()).filename().string();
  if (driver == "ccache" || driver == "sccache" || driver == "distcc")
    first = 2;
  for (std::size_t i = first; i < raw.size(); ++i)
    command->compile_arguments.push_back(raw[i]);
  // Overrides are options, even when the database terminates its options with
  // '--' before the source filename.
  const auto separator = std::find(command->compile_arguments.begin(),
                                   command->compile_arguments.end(), "--");
  command->compile_arguments.insert(separator, input.compile_arguments.begin(),
                                    input.compile_arguments.end());
  command->compilation_database = database->string();
  return *command;
}

FileInput resolve_snippet_compilation_command(const FileInput &input) {
  if (!input.path.empty())
    return resolve_compilation_command(input);
  if (input.compilation_profile_frozen)
    return input;
  const auto working = fs::absolute(input.working_directory.empty()
                                        ? fs::current_path()
                                        : fs::path(input.working_directory));
  const auto database = discover(input, working / "ctk-snippet.cpp", working);
  if (!database)
    return input;
  // Clang's database enumeration can group commands by filename. The fallback
  // deliberately means the first entry written in compile_commands.json.
  const auto bytes = llvm::MemoryBuffer::getFile(database->string());
  if (!bytes)
    throw std::invalid_argument("cannot read compilation database: " +
                                database->string());
  auto json = llvm::json::parse((*bytes)->getBuffer());
  if (!json)
    throw std::invalid_argument("cannot load compilation database " +
                                database->string() + ": " +
                                llvm::toString(json.takeError()));
  const auto *entries = json->getAsArray();
  if (!entries)
    throw std::invalid_argument("compilation database must be a JSON array: " +
                                database->string());
  if (entries->empty())
    throw std::invalid_argument("compilation database has no entries: " +
                                database->string());
  const auto *entry = entries->front().getAsObject();
  const auto source = entry ? entry->getString("file") : std::nullopt;
  const auto directory = entry ? entry->getString("directory") : std::nullopt;
  if (!source || !directory || source->empty())
    throw std::invalid_argument("invalid first compilation database entry: " +
                                database->string());
  FileInput selected = input;
  selected.path = absolute(source->str(),
                           absolute(directory->str(), database->parent_path()))
                      .string();
  selected.compilation_database = database->string();
  return resolve_compilation_command(selected);
}
FileInput transfer_snippet_compilation_command(
    FileInput donor, const std::vector<std::string> &overrides) {
  if (!donor.path.empty()) {
    // Expand in the donor CWD before transferring language/standard flags.
    // In particular, a C command's -std=c17 must not leak into C++ parsing.
    llvm::IntrusiveRefCntPtr<llvm::vfs::FileSystem> filesystem(
        llvm::vfs::createPhysicalFileSystem().release());
    if (auto error =
            filesystem->setCurrentWorkingDirectory(donor.working_directory))
      throw std::invalid_argument("cannot use compilation working directory: " +
                                  error.message());
    auto database = clang::tooling::expandResponseFiles(
        std::make_unique<clang::tooling::FixedCompilationDatabase>(
            donor.working_directory, donor.compile_arguments),
        filesystem);
    auto command = database->getCompileCommands(donor.path).front();
    command.CommandLine.front() = "clang";
    command = clang::tooling::transferCompileCommand(std::move(command),
                                                     "ctk-snippet.cpp");
    donor.compile_arguments.assign(command.CommandLine.begin() + 1,
                                   command.CommandLine.end());
  }
  const auto separator = std::find(donor.compile_arguments.begin(),
                                   donor.compile_arguments.end(), "--");
  donor.compile_arguments.insert(separator, overrides.begin(), overrides.end());
  return donor;
}
} // namespace ctk::clang_layer
