#include "ctk/clang/tooling.hpp"

#include <clang/AST/ASTContext.h>
#include <clang/AST/Decl.h>
#include <clang/AST/Expr.h>
#include <clang/AST/ExprCXX.h>
#include <clang/AST/Type.h>
#include <clang/ASTMatchers/ASTMatchFinder.h>
#include <clang/ASTMatchers/Dynamic/Diagnostics.h>
#include <clang/ASTMatchers/Dynamic/Parser.h>
#include <clang/Basic/SourceManager.h>
#include <clang/Frontend/ASTUnit.h>
#include <clang/Lex/Preprocessor.h>
#include <clang/Tooling/Tooling.h>
#include <llvm/ADT/IntrusiveRefCntPtr.h>
#include <llvm/ADT/SmallString.h>
#include <llvm/Support/MemoryBuffer.h>
#include <llvm/Support/Path.h>

#include <algorithm>
#include <condition_variable>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <sstream>
#include <string_view>
#include <unordered_map>
#include <utility>

namespace ctk::clang_layer {
namespace {

template <typename Function> class ScopeExit {
public:
  explicit ScopeExit(Function function) : function_(std::move(function)) {}
  ScopeExit(const ScopeExit &) = delete;
  ScopeExit &operator=(const ScopeExit &) = delete;
  ~ScopeExit() noexcept {
    if (active_) {
      try {
        function_();
      } catch (...) {
      }
    }
  }
  void release() noexcept { active_ = false; }

private:
  Function function_;
  bool active_ = true;
};

std::string normalized_path(const FileInput &file) {
  llvm::SmallString<256> path(file.path);
  if (llvm::sys::path::is_relative(path) && !file.working_directory.empty()) {
    llvm::SmallString<256> combined(file.working_directory);
    llvm::sys::path::append(combined, path);
    path = combined;
  }
  llvm::sys::path::remove_dots(path, true);
  return path.str().str();
}

std::string profile_for(const FileInput &file) {
  std::string profile;
  const auto append = [&](const std::string &value) {
    profile.append(std::to_string(value.size())).push_back(':');
    profile.append(value);
  };
  append(normalized_path(file));
  append(file.working_directory);
  profile.append(std::to_string(file.compile_arguments.size())).push_back(';');
  for (const auto &argument : file.compile_arguments) {
    append(argument);
  }
  return profile;
}

std::string
diagnostics_text(const clang::ast_matchers::dynamic::Diagnostics &diagnostics) {
  return diagnostics.toStringFull();
}

std::uint64_t ast_memory(const clang::ASTUnit &unit) {
  const auto &context = unit.getASTContext();
  const auto &source_manager = unit.getSourceManager();
  const auto buffers = source_manager.getMemoryBufferSizes();
  return static_cast<std::uint64_t>(context.getASTAllocatedMemory()) +
         static_cast<std::uint64_t>(context.getSideTableAllocatedMemory()) +
         static_cast<std::uint64_t>(source_manager.getContentCacheSize()) +
         static_cast<std::uint64_t>(source_manager.getDataStructureSizes()) +
         static_cast<std::uint64_t>(buffers.malloc_bytes) +
         static_cast<std::uint64_t>(buffers.mmap_bytes) +
         static_cast<std::uint64_t>(unit.getPreprocessor().getTotalMemory());
}

bool file_matches(const std::string &path, llvm::StringRef expected) {
  std::ifstream input(path, std::ios::binary);
  if (!input)
    return false;
  char buffer[8192];
  std::size_t offset = 0;
  while (offset < expected.size()) {
    const auto requested = std::min(sizeof(buffer), expected.size() - offset);
    input.read(buffer, static_cast<std::streamsize>(requested));
    const auto count = static_cast<std::size_t>(input.gcount());
    if (count == 0 || std::string_view(buffer, count) !=
                          std::string_view(expected.data() + offset, count))
      return false;
    offset += count;
  }
  return input.peek() == std::char_traits<char>::eof();
}

using DependencyBuffers =
    std::unordered_map<std::string, std::optional<llvm::StringRef>>;

DependencyBuffers dependency_buffers(const clang::ASTUnit &unit,
                                     const std::string &working_directory) {
  DependencyBuffers buffers;
  const auto &source_manager = unit.getSourceManager();
  for (auto file = source_manager.fileinfo_begin();
       file != source_manager.fileinfo_end(); ++file) {
    std::filesystem::path path(file->first.getName().str());
    if (path.is_relative() && !working_directory.empty())
      path = std::filesystem::path(working_directory) / path;
    const auto normalized = path.lexically_normal().string();
    buffers.try_emplace(normalized, file->second->getBufferDataIfLoaded());
  }
  return buffers;
}

bool dependencies_current(const DependencyBuffers &buffers,
                          const IQueryEngine::Checkpoint &checkpoint) {
  for (const auto &[path, buffer] : buffers) {
    if (!checkpoint() || !buffer || !file_matches(path, *buffer))
      return false;
  }
  return !buffers.empty();
}

SemanticBinding serialize(const clang::DynTypedNode &node,
                          const clang::PrintingPolicy &policy) {
  SemanticBinding binding;
  binding.kind = node.getNodeKind().asStringRef().str();
  if (const auto *named = node.get<clang::NamedDecl>()) {
    binding.name = named->getNameAsString();
  } else if (const auto *reference = node.get<clang::DeclRefExpr>()) {
    binding.name = reference->getDecl()->getNameAsString();
  } else if (const auto *member = node.get<clang::MemberExpr>()) {
    binding.name = member->getMemberDecl()->getNameAsString();
  } else if (const auto *call = node.get<clang::CallExpr>()) {
    if (const auto *callee = call->getDirectCallee())
      binding.name = callee->getNameAsString();
  }
  if (const auto *value = node.get<clang::ValueDecl>()) {
    binding.type = value->getType().getAsString(policy);
  } else if (const auto *expression = node.get<clang::Expr>()) {
    binding.type = expression->getType().getAsString(policy);
  } else if (const auto *type = node.get<clang::Type>()) {
    binding.type = clang::QualType(type, 0).getAsString(policy);
  }
  return binding;
}

class NativeQueryEngine final : public IQueryEngine {
  struct Snapshot {
    std::unique_ptr<clang::ASTUnit> unit;
    DependencyBuffers dependencies;
    std::mutex initialization_mutex;
    std::condition_variable initialized_cv;
    bool initialized = false;
    bool reuse_eligible = false;
    std::string initialization_error;
    std::mutex access_mutex;
  };

  struct Callback final : clang::ast_matchers::MatchFinder::MatchCallback {
    Callback(const Checkpoint &checkpoint,
             const IQueryEngine::MatchCallback &callback)
        : checkpoint(checkpoint), callback(callback) {}

    void
    run(const clang::ast_matchers::MatchFinder::MatchResult &result) override {
      if (!checkpoint())
        return;
      clang::PrintingPolicy policy(result.Context->getLangOpts());
      Bindings bindings;
      for (const auto &[id, node] : result.Nodes.getMap()) {
        bindings.emplace(id, serialize(node, policy));
      }
      callback(bindings);
    }

    const Checkpoint &checkpoint;
    const IQueryEngine::MatchCallback &callback;
  };

public:
  QueryResult match(const FileInput &file, const std::string &query,
                    const Checkpoint &checkpoint,
                    const MatchCallback &on_match) override {
    QueryResult result;
    result.profile = profile_for(file);
    const auto profile_lock = lock_for_profile(result.profile);
    std::unique_lock profile_guard(*profile_lock);
    if (!checkpoint()) {
      result.cancelled = true;
      result.message = "query cancelled";
      return result;
    }

    clang::ast_matchers::dynamic::Diagnostics diagnostics;
    llvm::StringRef query_text(query);
    auto matcher = clang::ast_matchers::dynamic::Parser::parseMatcherExpression(
        query_text, &diagnostics);
    if (!matcher) {
      result.message = diagnostics_text(diagnostics);
      return result;
    }

    std::shared_ptr<Snapshot> snapshot;
    std::unique_lock<std::mutex> snapshot_lock;
    for (;;) {
      if (!checkpoint()) {
        result.cancelled = true;
        result.message = "query cancelled";
        return result;
      }
      snapshot = get_snapshot(file, result.message, result.snapshot_evicted);
      if (!snapshot)
        return result;
      snapshot_lock = std::unique_lock(snapshot->access_mutex);
      if (snapshot->reuse_eligible &&
          dependencies_current(snapshot->dependencies, checkpoint))
        break;
      if (!snapshot->reuse_eligible)
        break;
      snapshot_lock.unlock();
      if (!checkpoint()) {
        result.cancelled = true;
        result.message = "query cancelled";
        result.snapshot_retained = true;
        result.native_memory_bytes = ast_memory(*snapshot->unit);
        return result;
      }
      {
        std::lock_guard map_lock(snapshots_mutex_);
        const auto current = snapshots_.find(result.profile);
        if (current != snapshots_.end() && current->second == snapshot)
          snapshots_.erase(current);
      }
      snapshot->unit.reset();
      snapshot->dependencies.clear();
      result.snapshot_evicted = true;
      snapshot.reset();
    }
    if (!checkpoint()) {
      result.cancelled = true;
      result.message = "query cancelled";
      result.snapshot_retained = true;
      result.native_memory_bytes = ast_memory(*snapshot->unit);
      return result;
    }

    Callback callback(checkpoint, on_match);
    clang::ast_matchers::MatchFinder finder;
    if (!finder.addDynamicMatcher(*matcher, &callback)) {
      result.message =
          "matcher is valid but cannot be used as a top-level AST matcher";
      result.snapshot_retained = true;
      result.native_memory_bytes = ast_memory(*snapshot->unit);
      return result;
    }
    finder.matchAST(snapshot->unit->getASTContext());
    result.cancelled = !checkpoint();
    result.ok = !result.cancelled;
    result.snapshot_retained = true;
    result.message = result.cancelled ? "query cancelled" : std::string{};
    result.native_memory_bytes = ast_memory(*snapshot->unit);
    return result;
  }

private:
  std::shared_ptr<Snapshot> get_snapshot(const FileInput &file,
                                         std::string &error, bool &evicted) {
    const auto key = profile_for(file);
    std::shared_ptr<Snapshot> snapshot;
    bool initialize = false;
    std::shared_ptr<Snapshot> retired_snapshot;
    {
      std::lock_guard lock(snapshots_mutex_);
      auto found = snapshots_.find(key);
      if (found != snapshots_.end()) {
        snapshot = found->second;
        std::lock_guard state_lock(snapshot->initialization_mutex);
        if (snapshot->initialized && !snapshot->reuse_eligible) {
          retired_snapshot = snapshot;
          snapshots_.erase(found);
          snapshot = std::make_shared<Snapshot>();
          snapshots_.emplace(key, snapshot);
          initialize = true;
          evicted = true;
        }
      } else {
        snapshot = std::make_shared<Snapshot>();
        snapshots_.emplace(key, snapshot);
        initialize = true;
      }
    }
    if (retired_snapshot) {
      retired_snapshot->unit.reset();
      retired_snapshot->dependencies.clear();
      retired_snapshot.reset();
    }
    if (initialize) {
      std::unique_ptr<clang::ASTUnit> unit;
      auto initialization_guard = ScopeExit([&] {
        {
          std::lock_guard lock(snapshot->initialization_mutex);
          snapshot->initialized = true;
        }
        snapshot->initialized_cv.notify_all();
        std::lock_guard lock(snapshots_mutex_);
        const auto found = snapshots_.find(key);
        if (found != snapshots_.end() && found->second == snapshot &&
            !snapshot->unit)
          snapshots_.erase(found);
      });
      try {
        const auto path = normalized_path(file);
        if (std::ifstream source_file(path, std::ios::binary); !source_file) {
          snapshot->initialization_error = "cannot open source file: " + path;
        } else {
          std::ostringstream source;
          source << source_file.rdbuf();
          auto arguments = file.compile_arguments;
          if (std::none_of(arguments.begin(), arguments.end(),
                           [](const auto &arg) {
                             return arg == "-x" || arg.starts_with("-x=") ||
                                    arg.starts_with("-x");
                           })) {
            arguments.emplace_back("-x");
            arguments.emplace_back("c++");
          }
          if (std::none_of(
                  arguments.begin(), arguments.end(),
                  [](const auto &arg) { return arg.starts_with("-std="); })) {
            arguments.emplace_back("-std=c++20");
          }
#ifdef CTK_CLANG_RESOURCE_DIR
          arguments.emplace_back(std::string("-resource-dir=") +
                                 CTK_CLANG_RESOURCE_DIR);
#endif
          if (!file.working_directory.empty()) {
            arguments.push_back("-working-directory=" + file.working_directory);
          }
          unit = clang::tooling::buildASTFromCodeWithArgs(source.str(),
                                                          arguments, path,
#ifdef CTK_CLANG_TOOL_PATH
                                                          CTK_CLANG_TOOL_PATH
#else
                                                          "clang-tool"
#endif
          );
          if (!unit) {
            snapshot->initialization_error =
                "Clang could not build an AST for " + path;
          } else if (unit->getDiagnostics().hasErrorOccurred()) {
            snapshot->initialization_error =
                "Clang reported errors while parsing " + path;
            unit.reset();
          }
        }
        if (unit)
          snapshot->dependencies =
              dependency_buffers(*unit, file.working_directory);
        if (unit)
          snapshot->reuse_eligible =
              cache_reuse_allowed(file, snapshot->dependencies);
      } catch (const std::exception &exception) {
        try {
          snapshot->initialization_error =
              std::string("AST initialization failed: ") + exception.what();
        } catch (...) {
        }
        unit.reset();
      } catch (...) {
        try {
          snapshot->initialization_error =
              "AST initialization failed with an unknown error";
        } catch (...) {
        }
        unit.reset();
      }
      {
        std::lock_guard lock(snapshot->initialization_mutex);
        snapshot->unit = std::move(unit);
        snapshot->initialized = true;
      }
      initialization_guard.release();
      snapshot->initialized_cv.notify_all();
      if (!snapshot->unit) {
        std::lock_guard lock(snapshots_mutex_);
        const auto found = snapshots_.find(key);
        if (found != snapshots_.end() && found->second == snapshot)
          snapshots_.erase(found);
      }
    } else {
      std::unique_lock lock(snapshot->initialization_mutex);
      snapshot->initialized_cv.wait(lock,
                                    [&] { return snapshot->initialized; });
    }
    if (!snapshot->unit) {
      error = snapshot->initialization_error;
      return {};
    }
    return snapshot;
  }

  std::mutex snapshots_mutex_;
  std::unordered_map<std::string, std::shared_ptr<Snapshot>> snapshots_;
  std::mutex profile_locks_mutex_;
  std::unordered_map<std::string, std::weak_ptr<std::mutex>> profile_locks_;

  std::shared_ptr<std::mutex> lock_for_profile(const std::string &key) {
    std::lock_guard lock(profile_locks_mutex_);
    std::erase_if(profile_locks_,
                  [](const auto &entry) { return entry.second.expired(); });
    auto &weak = profile_locks_[key];
    auto mutex = weak.lock();
    if (!mutex) {
      mutex = std::make_shared<std::mutex>();
      weak = mutex;
    }
    return mutex;
  }

  bool cache_reuse_allowed(const FileInput &file,
                           const DependencyBuffers &dependencies) const {
    if (dependencies.size() != 1)
      return false;
    const auto main_path = normalized_path(file);
    const auto main = dependencies.find(main_path);
    if (main == dependencies.end() || !main->second)
      return false;
    if (main->second->contains("#") || main->second->contains("%:") ||
        main->second->contains("?"
                               "?=") ||
        main->second->contains("__has_include") ||
        main->second->contains("__has_embed") ||
        main->second->contains("import"))
      return false;
    return std::none_of(file.compile_arguments.begin(),
                        file.compile_arguments.end(), [](const auto &argument) {
                          return argument.starts_with("-include") ||
                                 argument.starts_with("-imacros") ||
                                 argument.starts_with("-fmodule") ||
                                 argument.starts_with("-fprebuilt-module") ||
                                 argument.ends_with(".pch");
                        });
  }
};

} // namespace

std::shared_ptr<IQueryEngine> make_query_engine() {
  return std::make_shared<NativeQueryEngine>();
}

std::vector<std::string> match(const Project &, const std::string &) {
  return {};
}
std::string cfg(const Project &, const std::string &) { return {}; }
std::string callgraph(const Project &) { return {}; }

} // namespace ctk::clang_layer
