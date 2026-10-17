#include "ctk/clang/project_index_extract.hpp"
#include "ctk/cache/include_inventory.hpp"
#include "snapshot/compilation_environment.hpp"
#include <algorithm>
#include <clang/AST/ASTConsumer.h>
#include <clang/AST/RecursiveASTVisitor.h>
#include <clang/Basic/Diagnostic.h>
#include <clang/Basic/SourceManager.h>
#include <clang/Basic/Version.h>
#include <clang/Frontend/FrontendAction.h>
#include <clang/Index/USRGeneration.h>
#include <clang/Tooling/ArgumentsAdjusters.h>
#include <clang/Tooling/CompilationDatabase.h>
#include <clang/Tooling/JSONCompilationDatabase.h>
#include <clang/Tooling/Tooling.h>
#include <filesystem>
#include <fstream>
#include <string_view>
#include <llvm/ADT/SmallString.h>
#include <llvm/Support/SHA256.h>
#include <llvm/Support/VirtualFileSystem.h>
#include <tuple>

namespace ctk::clang_layer {
namespace fs = std::filesystem;
namespace {
std::string canonical(const std::string &value) {
  std::error_code ec;
  auto p = fs::weakly_canonical(value, ec);
  return (ec ? fs::absolute(value).lexically_normal() : p).string();
}
std::string digest(const std::string &path) {
  std::ifstream in(path, std::ios::binary);
  if (!in)
    return {};
  llvm::SHA256 hash;
  char data[65536];
  while (in) {
    in.read(data, sizeof(data));
    if (in.gcount() > 0)
      hash.update(llvm::ArrayRef<uint8_t>(reinterpret_cast<uint8_t *>(data),
                                          static_cast<size_t>(in.gcount())));
  }
  return llvm::toHex(llvm::ArrayRef<uint8_t>(hash.final()), true);
}
std::string digest_buffer(llvm::StringRef buffer) {
  llvm::SHA256 hash;
  hash.update(buffer);
  return llvm::toHex(llvm::ArrayRef<uint8_t>(hash.final()), true);
}
std::string json_string(const std::string &value) {
  std::string out = "\"";
  for (unsigned char c : value) {
    switch (c) {
    case '\\':
      out += "\\\\";
      break;
    case '\"':
      out += "\\\"";
      break;
    case '\n':
      out += "\\n";
      break;
    case '\r':
      out += "\\r";
      break;
    case '\t':
      out += "\\t";
      break;
    default:
      if (c < 0x20) {
        static constexpr char h[] = "0123456789abcdef";
        out += "\\u00";
        out += h[c >> 4];
        out += h[c & 15];
      } else
        out += static_cast<char>(c);
    }
  }
  out += '\"';
  return out;
}
class Visitor : public clang::RecursiveASTVisitor<Visitor> {
public:
  Visitor(clang::ASTContext &c, ProjectIndexExtraction &r)
      : context(c), output(r) {}
  bool VisitNamedDecl(clang::NamedDecl *d) {
    if (d->isImplicit() || d->getNameAsString().empty() ||
        !d->getLocation().isValid())
      return true;
    llvm::SmallString<128> usr;
    if (clang::index::generateUSRForDecl(d, usr))
      return true;
    auto &sm = context.getSourceManager();
    auto loc = sm.getSpellingLoc(d->getLocation());
    const auto file_name = sm.getFilename(loc);
    if (file_name.empty())
      return true;
    IndexedSymbol s;
    s.usr = usr.str().str();
    s.name = d->getNameAsString();
    s.qualified_name = d->getQualifiedNameAsString();
    s.kind = d->getDeclKindName();
    s.file_path = canonical(file_name.str());
    s.line = sm.getSpellingLineNumber(loc);
    s.column = sm.getSpellingColumnNumber(loc);
    s.byte_offset = sm.getFileOffset(loc);
    if (auto *f = llvm::dyn_cast<clang::FunctionDecl>(d)) {
      s.is_definition = f->isThisDeclarationADefinition();
      s.signature = f->getType().getAsString();
    } else if (auto *v = llvm::dyn_cast<clang::VarDecl>(d)) {
      s.is_definition = v->isThisDeclarationADefinition();
      s.signature = v->getType().getAsString();
    } else if (auto *t = llvm::dyn_cast<clang::TagDecl>(d))
      s.is_definition = t->isThisDeclarationADefinition();
    output.symbols.push_back(std::move(s));
    return true;
  }
  clang::ASTContext &context;
  ProjectIndexExtraction &output;
};
class Consumer final : public clang::ASTConsumer {
public:
  explicit Consumer(Visitor &v) : visitor(v) {}
  void HandleTranslationUnit(clang::ASTContext &c) override {
    visitor.TraverseDecl(c.getTranslationUnitDecl());
  }

private:
  Visitor &visitor;
};
class Action final : public clang::ASTFrontendAction {
public:
  explicit Action(ProjectIndexExtraction &r) : result(r) {}
  std::unique_ptr<clang::ASTConsumer>
  CreateASTConsumer(clang::CompilerInstance &, llvm::StringRef) override {
    visitor = std::make_unique<Visitor>(getCompilerInstance().getASTContext(),
                                        result);
    return std::make_unique<Consumer>(*visitor);
  }
  void EndSourceFileAction() override {
    auto &sm = getCompilerInstance().getSourceManager();
    const auto capture = [&](const clang::SrcMgr::SLocEntry &entry) {
      if (entry.isFile()) {
        const auto &cache = entry.getFile().getContentCache();
        if (auto file = cache.OrigEntry) {
          auto path = canonical(file->getName().str());
          auto buffer =
              cache.getBufferOrNone(getCompilerInstance().getDiagnostics(),
                                    getCompilerInstance().getFileManager());
          if (buffer)
            result.dependencies.insert_or_assign(
                path, digest_buffer(buffer->getBuffer()));
        }
      }
    };
    for (unsigned i = 0; i < sm.local_sloc_entry_size(); ++i)
      capture(sm.getLocalSLocEntry(i));
    for (unsigned i = 0; i < sm.loaded_sloc_entry_size(); ++i) {
      bool invalid = false;
      const auto &entry = sm.getLoadedSLocEntry(i, &invalid);
      if (!invalid)
        capture(entry);
    }
  }

private:
  ProjectIndexExtraction &result;
  std::unique_ptr<Visitor> visitor;
};
class Factory final : public clang::tooling::FrontendActionFactory {
public:
  explicit Factory(ProjectIndexExtraction &r) : result(r) {}
  std::unique_ptr<clang::FrontendAction> create() override {
    return std::make_unique<Action>(result);
  }

private:
  ProjectIndexExtraction &result;
};

class IndexDiagnosticConsumer final : public clang::DiagnosticConsumer {
public:
  void HandleDiagnostic(clang::DiagnosticsEngine::Level level,
                        const clang::Diagnostic &diagnostic) override {
    clang::DiagnosticConsumer::HandleDiagnostic(level, diagnostic);
    if (level >= clang::DiagnosticsEngine::Error && first_error.empty()) {
      llvm::SmallString<256> message;
      diagnostic.FormatDiagnostic(message);
      first_error = message.str().str();
    }
  }

  std::string first_error;
};

class SingleCommandDatabase final : public clang::tooling::CompilationDatabase {
public:
  SingleCommandDatabase(const std::string &source, const std::string &directory,
                        const std::vector<std::string> &arguments) {
    command_.Directory = directory;
    command_.Filename = source;
    // Use the configured driver rather than FixedCompilationDatabase's
    // synthetic clang-tool name: driver defaults must match CTK's native parser
    // and the matching compiler that produced a PCH.
    command_.CommandLine = {CTK_CLANG_TOOL_PATH};
    if (source.ends_with(".c") &&
        std::none_of(arguments.begin(), arguments.end(), [](const auto &arg) {
          return arg.starts_with("-std=") &&
                 arg.find("++") != std::string::npos;
        }))
      command_.CommandLine.push_back("--driver-mode=gcc");
    command_.CommandLine.insert(command_.CommandLine.end(), arguments.begin(),
                                arguments.end());
    command_.CommandLine.push_back(source);
  }
  std::vector<clang::tooling::CompileCommand>
  getCompileCommands(llvm::StringRef) const override {
    return {command_};
  }

private:
  clang::tooling::CompileCommand command_;
};
} // namespace

std::string
serialize_project_index_context(const std::string &directory,
                                const std::vector<std::string> &arguments,
                                const std::string &compiler) {
  std::string out =
      "{\"directory\":" + json_string(directory) +
      ",\"compiler\":" + json_string(compiler) +
      ",\"toolchain\":" + json_string(clang::getClangFullVersion()) +
      ",\"arguments\":[";
  for (std::size_t i = 0; i < arguments.size(); ++i) {
    if (i)
      out += ',';
    out += json_string(arguments[i]);
  }
  out += "],\"environment\":[";
  bool first = true;
  for (const auto &[key, value] : snapshot::compilation_environment()) {
    if (!first)
      out += ',';
    first = false;
    out += '[' + json_string(key) + ',' + json_string(value) + ']';
  }
  out += "]}";
  return out;
}

bool extract_project_index(const std::string &source,
                           const std::string &directory,
                           const std::string &working_directory,
                           const std::vector<std::string> &arguments,
                           ProjectIndexExtraction &result, std::string &error) {
  (void)directory;
  result.compile_context =
      serialize_project_index_context(working_directory, arguments);
  std::set<std::string> include_roots{
      canonical(fs::path(source).parent_path().string())};
  for (std::size_t i = 0; i < arguments.size(); ++i) {
    const auto &argument = arguments[i];
    std::string path;
    if ((argument == "-I" || argument == "-iquote" || argument == "-isystem" ||
         argument == "-idirafter" || argument == "-F" ||
         argument == "-iframework") &&
        i + 1 < arguments.size())
      path = arguments[++i];
    else if (argument.starts_with("-I") && argument.size() > 2)
      path = argument.substr(2);
    else {
      for (const char *option : {"-iquote", "-isystem", "-idirafter", "-F",
                                 "-iframework"}) {
        const std::string_view prefix(option);
        if (argument.starts_with(prefix) && argument.size() > prefix.size()) {
          path = argument.substr(prefix.size());
          break;
        }
      }
    }
    if (!path.empty())
      include_roots.insert(canonical((fs::path(path).is_absolute()
                                          ? fs::path(path)
                                          : fs::path(working_directory) / path)
                                         .string()));
  }
  for (const auto &root : include_roots)
    result.dependencies.insert_or_assign(
        "@include-tree:" + root, digest_buffer(cache::include_inventory(root)));
  for (std::size_t i = 0; i < arguments.size(); ++i) {
    std::string input;
    const auto &arg = arguments[i];
    if (arg == "-include-pch" || arg == "-include-pth" ||
        arg == "-fmodule-file" || arg == "-fmodule-map-file") {
      if (i + 1 < arguments.size() && arguments[i + 1] == "-Xclang")
        ++i;
      if (i + 1 < arguments.size())
        input = arguments[++i];
    } else if (arg.starts_with("-fmodule-file=") ||
               arg.starts_with("-fmodule-map-file=")) {
      input = arg.substr(arg.find('=') + 1);
      if (arg.starts_with("-fmodule-file=") &&
          input.find('=') != std::string::npos)
        input = input.substr(input.find('=') + 1);
    }
    if (!input.empty()) {
      const auto path = canonical((fs::path(input).is_absolute()
                                       ? fs::path(input)
                                       : fs::path(working_directory) / input)
                                      .string());
      result.dependencies.insert_or_assign(path, digest(path));
    }
  }
  SingleCommandDatabase fixed(source, working_directory, arguments);
  Factory factory(result);
  clang::tooling::ClangTool tool(fixed, {source});
  IndexDiagnosticConsumer diagnostics;
  tool.setDiagnosticConsumer(&diagnostics);
  if (tool.run(&factory) != 0 || !diagnostics.first_error.empty()) {
    error = "Clang failed to index translation unit: " + source;
    if (!diagnostics.first_error.empty())
      error += ": " + diagnostics.first_error;
    return false;
  }
  return true;
}
bool list_project_translation_units(const std::string &directory,
                                    std::vector<ProjectIndexCommand> &units,
                                    std::string &error) {
  std::unique_ptr<clang::tooling::CompilationDatabase> db =
      clang::tooling::JSONCompilationDatabase::loadFromDirectory(directory,
                                                                 error);
  if (!db)
    return false;
  db = clang::tooling::expandResponseFiles(std::move(db),
                                           llvm::vfs::getRealFileSystem());
  db = clang::tooling::inferToolLocation(std::move(db));
  for (const auto &source : db->getAllFiles()) {
    const auto canonical_source = canonical(source);
    auto commands = db->getCompileCommands(canonical_source);
    if (commands.empty())
      continue;
    for (const auto &command : commands) {
      ProjectIndexCommand unit;
      unit.source = canonical_source;
      unit.working_directory = canonical(command.Directory);
      auto args = command.CommandLine;
      const auto compiler = args.empty() ? std::string() : args.front();
      args = clang::tooling::getClangStripDependencyFileAdjuster()(
          args, canonical_source);
      args =
          clang::tooling::getClangStripOutputAdjuster()(args, canonical_source);
      args =
          clang::tooling::getClangSyntaxOnlyAdjuster()(args, canonical_source);
      for (size_t i = 1; i < args.size(); ++i) {
        const auto &arg = args[i];
        if (arg == "--")
          continue;
        std::error_code ec;
        const auto argument_path = fs::path(arg);
        auto maybe_source = fs::weakly_canonical(
            argument_path.is_absolute()
                ? argument_path
                : fs::path(unit.working_directory) / argument_path,
            ec);
        if (!ec && maybe_source == fs::path(canonical_source))
          continue;
        unit.arguments.push_back(arg);
      }
      unit.arguments.insert(unit.arguments.begin(),
                            "-resource-dir=" CTK_CLANG_RESOURCE_DIR);
      unit.serialized_context = serialize_project_index_context(
          unit.working_directory, unit.arguments, compiler);
      units.push_back(std::move(unit));
    }
  }
  std::sort(units.begin(), units.end(), [](const auto &a, const auto &b) {
    return std::tie(a.source, a.working_directory, a.arguments) <
           std::tie(b.source, b.working_directory, b.arguments);
  });
  units.erase(std::unique(units.begin(), units.end(),
                          [](const auto &a, const auto &b) {
                            return a.source == b.source &&
                                   a.working_directory == b.working_directory &&
                                   a.arguments == b.arguments;
                          }),
              units.end());
  return true;
}
} // namespace ctk::clang_layer
