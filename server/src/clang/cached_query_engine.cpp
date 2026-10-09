#include "ctk/clang/tooling.hpp"
#include "ctk/clang/compilation_database.hpp"

#include "ctk/cache/compilation_context.hpp"
#include "ctk/cache/snapshot_cache.hpp"
#include "ctk/storage/store.hpp"
#include "native_snapshot_owner.hpp"
#include "native_temporary_artifact.hpp"
#include "serialization/node_serializers.hpp"
#include "snapshot/build_snapshot.hpp"
#include "snapshot/compilation_environment.hpp"
#include "snapshot/input_identity.hpp"

#include <clang/AST/ASTContext.h>
#include <clang/ASTMatchers/ASTMatchFinder.h>
#include <clang/ASTMatchers/Dynamic/Diagnostics.h>
#include <clang/ASTMatchers/Dynamic/Parser.h>
#include <clang/Basic/Diagnostic.h>
#include <clang/Basic/FileSystemOptions.h>
#include <clang/Basic/SourceManager.h>
#include <clang/Basic/Version.h>
#include <clang/Frontend/ASTUnit.h>
#include <clang/Lex/HeaderSearchOptions.h>
#include <clang/Lex/Preprocessor.h>
#include <clang/Serialization/PCHContainerOperations.h>
#include <clang/Tooling/Tooling.h>
#include <google/protobuf/struct.pb.h>
#include <google/protobuf/util/json_util.h>
#include <llvm/ADT/IntrusiveRefCntPtr.h>
#include <llvm/ADT/SmallString.h>
#include <llvm/ADT/StringExtras.h>
#include <llvm/Support/Path.h>
#include <llvm/Support/SHA256.h>
#include <llvm/Support/VirtualFileSystem.h>
#include <llvm/TargetParser/Host.h>

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <utility>

namespace ctk::clang_layer {
namespace {

std::filesystem::path storage_root() {
  if (const auto *configured = std::getenv("CTK_STORAGE_ROOT");
      configured != nullptr && *configured != '\0')
    return configured;
  if (const auto *cache_home = std::getenv("XDG_CACHE_HOME");
      cache_home != nullptr && *cache_home != '\0')
    return std::filesystem::path(cache_home) / "clang-toolkit" / "storage";
  if (const auto *user_home = std::getenv("HOME");
      user_home != nullptr && *user_home != '\0')
    return std::filesystem::path(user_home) / ".cache" / "clang-toolkit" /
           "storage";
  return std::filesystem::temp_directory_path() / "clang-toolkit-storage";
}

std::shared_ptr<ctk::storage::Store> shared_store() {
  static const auto store = []() -> std::shared_ptr<ctk::storage::Store> {
    try {
      ctk::storage::StoreOptions options;
      options.root = storage_root();
      return std::shared_ptr<ctk::storage::Store>(
          ctk::storage::Store::open(std::move(options)));
    } catch (...) {
      return {};
    }
  }();
  return store;
}

std::string normalized_path(const FileInput &file) {
  std::filesystem::path path(file.path);
  if (path.is_relative() && !file.working_directory.empty())
    path = std::filesystem::path(file.working_directory) / path;
  return path.lexically_normal().string();
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
  std::string current((std::istreambuf_iterator<char>(input)), {});
  return current == expected;
}

DependencyBuffers dependency_buffers(const clang::ASTUnit &unit,
                                     const std::string &working_directory) {
  DependencyBuffers buffers;
  const auto &source_manager = unit.getSourceManager();
  for (auto file = source_manager.fileinfo_begin();
       file != source_manager.fileinfo_end(); ++file) {
    std::filesystem::path path(file->first.getName().str());
    if (path.is_relative() && !working_directory.empty())
      path = std::filesystem::path(working_directory) / path;
    buffers.try_emplace(path.string(), file->second->getBufferDataIfLoaded());
  }
  return buffers;
}

bool reusable_file_candidate(const FileInput &file) {
  std::ifstream input(normalized_path(file), std::ios::binary);
  if (!input)
    return false;
  const std::string source((std::istreambuf_iterator<char>(input)), {});
  return std::none_of(file.compile_arguments.begin(),
                      file.compile_arguments.end(), [](const auto &argument) {
                        return argument.starts_with("@") ||
                               argument == "-Xclang" ||
                               argument.starts_with("-Wp,") ||
                               argument.starts_with("-fplugin") ||
                               argument == "-load" ||
                               argument.starts_with("-ivfsoverlay") ||
                               argument.starts_with("-fno-validate-pch") ||
                               argument.starts_with(
                                   "-fmodules-validate-once-per-build-session");
                      });
}

std::string sha256_hex(llvm::StringRef bytes) {
  static constexpr char digits[] = "0123456789abcdef";
  llvm::SHA256 hasher;
  hasher.update(bytes);
  const auto digest = hasher.final();
  std::string result;
  result.reserve(digest.size() * 2);
  for (const auto byte : digest) {
    result.push_back(digits[byte >> 4]);
    result.push_back(digits[byte & 0x0f]);
  }
  return result;
}

std::string resource_content_identity() {
  static const auto identity = [] {
#ifdef CTK_CLANG_RESOURCE_DIR
    const std::filesystem::path root(CTK_CLANG_RESOURCE_DIR);
#else
    const std::filesystem::path root;
#endif
    if (root.empty() || !std::filesystem::exists(root))
      return std::string{};
    std::vector<std::filesystem::path> files;
    std::error_code error;
    for (std::filesystem::recursive_directory_iterator iterator(root, error),
         end;
         !error && iterator != end; iterator.increment(error)) {
      if (iterator->is_regular_file(error))
        files.push_back(iterator->path());
    }
    if (error)
      return std::string{};
    std::ranges::sort(files);
    llvm::SHA256 hasher;
    for (const auto &path : files) {
      std::ifstream input(path, std::ios::binary);
      if (!input)
        return std::string{};
      const auto relative = path.lexically_relative(root).generic_string();
      hasher.update(relative);
      const std::string bytes((std::istreambuf_iterator<char>(input)), {});
      hasher.update(bytes);
    }
    const auto digest = hasher.final();
    static constexpr char digits[] = "0123456789abcdef";
    std::string result;
    result.reserve(digest.size() * 2);
    for (const auto byte : digest) {
      result.push_back(digits[byte >> 4]);
      result.push_back(digits[byte & 0x0f]);
    }
    return result;
  }();
  return identity;
}

std::vector<std::string> effective_arguments(const FileInput &file) {
  std::vector<std::string> arguments;
  if (std::none_of(file.compile_arguments.begin(), file.compile_arguments.end(),
                   [](const auto &arg) {
                     return arg == "-x" || arg.starts_with("-x=") ||
                            arg.starts_with("-x");
                   })) {
    arguments.emplace_back("-x");
    arguments.emplace_back("c++");
  }
  if (std::none_of(file.compile_arguments.begin(), file.compile_arguments.end(),
                   [](const auto &arg) { return arg.starts_with("-std="); }))
    arguments.emplace_back("-std=c++20");
#ifdef CTK_CLANG_RESOURCE_DIR
  arguments.emplace_back(std::string("-resource-dir=") +
                         CTK_CLANG_RESOURCE_DIR);
#endif
  if (!file.working_directory.empty())
    arguments.push_back("-working-directory=" + file.working_directory);
  // Defaults must precede response files and '--'; explicit compiler options
  // remain able to override defaults instead of becoming positional inputs.
  arguments.insert(arguments.end(), file.compile_arguments.begin(),
                   file.compile_arguments.end());
  return arguments;
}

ctk::cache::CompilationContext cache_context(const FileInput &file) {
  ctk::cache::CompilationContext context;
  context.input_spelling = file.path;
  context.working_directory = file.working_directory.empty()
                                  ? std::filesystem::current_path().string()
                                  : file.working_directory;
  context.toolchain_identity = clang::getClangFullVersion();
#ifdef CTK_CLANG_RESOURCE_DIR
  context.resource_directory = CTK_CLANG_RESOURCE_DIR;
#endif
  context.arguments = effective_arguments(file);
  context.environment = snapshot::compilation_environment();
  context.reusable = reusable_file_candidate(file);
  for (const auto &arg : context.arguments) {
    if (arg.starts_with("--target="))
      context.target = arg.substr(9);
    else if (arg.starts_with("--sysroot="))
      context.sysroot = arg.substr(10);
  }
  return context;
}

class ClangSnapshotLoader final : public ctk::cache::SnapshotLoader {
public:
  explicit ClangSnapshotLoader(std::shared_ptr<ctk::storage::Store> store)
      : store_(std::move(store)) {}

  ctk::cache::LoadedSnapshot
  load(const std::string &path,
       const ctk::cache::CompilationContext &context) override {
    std::ifstream source_file(path, std::ios::binary);
    if (!source_file)
      throw std::runtime_error("cannot open source file: " + path);
    std::ostringstream source;
    source << source_file.rdbuf();
    FileInput file{path, context.arguments, context.working_directory};
    auto arguments = effective_arguments(file);
    auto owner = std::make_shared<AstSnapshotOwner>();
    owner->environment = context.environment;
    owner->filesystem = snapshot::CapturedFileSystem::physical();
    auto unit = try_load_stored(file, context, *owner);
    std::string diagnostic_text;
    auto parse_source = [&] {
      unit = snapshot::build_snapshot(path, arguments,
#ifdef CTK_CLANG_TOOL_PATH
                                      CTK_CLANG_TOOL_PATH,
#else
                                      "clang-tool",
#endif
                                      owner->filesystem, owner->volatile_input,
                                      owner->writer, diagnostic_text);
    };
    if (!unit)
      parse_source();
    if (!unit || unit->getDiagnostics().hasErrorOccurred())
      throw std::runtime_error(
          "Clang could not build an AST for " + path +
          (diagnostic_text.empty() ? "" : "\n" + diagnostic_text));

    try {
      owner->artifact_closure = snapshot::capture_native_artifacts(
          *unit, *owner->filesystem, context.working_directory);
    } catch (const std::exception &error) {
      if (!owner->storage_loaded)
        throw;
      owner->storage_message = error.what();
      try {
        store_->mark_stale(owner->storage_lease->descriptor().id);
      } catch (...) {
      }
      unit.reset();
      owner->storage_lease.reset();
      owner->native_artifact.reset();
      owner->storage_loaded = false;
      owner->filesystem = snapshot::CapturedFileSystem::physical();
      parse_source();
      if (!unit || unit->getDiagnostics().hasErrorOccurred())
        throw std::runtime_error(
            "Clang could not build an AST for " + path +
            (diagnostic_text.empty() ? "" : "\n" + diagnostic_text));
      owner->artifact_closure = snapshot::capture_native_artifacts(
          *unit, *owner->filesystem, context.working_directory);
    }
    owner->dependencies = dependency_buffers(*unit, context.working_directory);
    bool invalid_main_buffer = false;
    const auto main_buffer = unit->getSourceManager().getBufferData(
        unit->getSourceManager().getMainFileID(), &invalid_main_buffer);
    if (!invalid_main_buffer)
      owner->dependencies.insert_or_assign(normalized_path(file), main_buffer);
    auto loaded = ctk::cache::LoadedSnapshot{};
    for (const auto &[input_path, buffer] : owner->dependencies)
      if (buffer)
        owner->filesystem->add_buffer(input_path, *buffer);
    owner->reusable = context.reusable && owner->filesystem->reusable() &&
                      owner->artifact_closure.reusable &&
                      !owner->volatile_input;
    owner->unit = std::move(unit);
    if (owner->reusable && !owner->storage_lease)
      publish_stored(file, context, *owner);
    // Serialization may consume additional compiler metadata (for example,
    // SDKSettings.json on Clang 21). Capture those lookups before freezing the
    // native view and copying its complete freshness observations.
    owner->reusable = owner->reusable && owner->filesystem->reusable();
    if (owner->filesystem->reusable() && owner->artifact_closure.reusable)
      owner->filesystem->seal();
    for (const auto &[input_path, input] : owner->filesystem->inputs())
      if (!input.staged)
        loaded.inputs.push_back(snapshot::cache_observation(input));
    // A noncapturable native view remains a fresh parse and is never retained.
    // Preserve actual consumed main bytes even when broader capture is
    // disabled.
    if (!owner->reusable) {
      loaded.inputs.clear();
      if (!invalid_main_buffer) {
        loaded.inputs.push_back(
            {normalized_path(file),
             ctk::cache::InputKind::File,
             sha256_hex(main_buffer),
             "native-source-buffer-v1",
             {}});
      }
    }
    loaded.reusable = owner->reusable;
    loaded.estimated_bytes =
        static_cast<std::size_t>(ast_memory(*owner->unit)) +
        owner->filesystem->estimated_bytes() +
        (owner->writer ? owner->writer->estimated_bytes() : 0);
    loaded.owner = std::move(owner);
    return loaded;
  }

  bool validate(const ctk::cache::SnapshotEntry &snapshot) override {
    const auto owner =
        std::static_pointer_cast<const AstSnapshotOwner>(snapshot.owner);
    if (!owner || !owner->unit || owner->dependencies.empty() ||
        owner->environment != snapshot::compilation_environment())
      return false;
    // Uncapturable views are freshly parsed and never admitted for reuse.
    // Their owned native buffers describe the parse, including virtual remaps.
    if (!owner->reusable)
      return true;
    for (const auto &[path, buffer] : owner->dependencies) {
      if (!buffer || !file_matches(path, *buffer))
        return false;
    }
    return !owner->reusable || owner->filesystem->validate();
  }

private:
  ctk::storage::CompilationProfile
  storage_profile(const FileInput &file,
                  const ctk::cache::CompilationContext &context) const {
    ctk::storage::CompilationProfile profile;
    profile.main_path = normalized_path(file);
    profile.toolchain.clang_version = clang::getClangFullVersion();
    profile.toolchain.build_identity =
#ifdef CTK_CLANG_TOOL_PATH
        CTK_CLANG_TOOL_PATH;
#else
        "clang-tool";
#endif
    profile.toolchain.target_triple = context.target.empty()
                                          ? llvm::sys::getDefaultTargetTriple()
                                          : context.target;
    profile.toolchain.resource_directory = context.resource_directory;
    profile.toolchain.resource_content_identity = resource_content_identity();
    profile.input_spelling = file.path;
    profile.working_directory = context.working_directory;
    profile.sysroot = context.sysroot;
    profile.arguments = context.arguments;
    profile.environment = context.environment;
    profile.reusable = context.reusable;
    return profile;
  }

  std::unique_ptr<clang::ASTUnit>
  load_ast_file(const std::filesystem::path &path,
                llvm::IntrusiveRefCntPtr<llvm::vfs::FileSystem> filesystem,
                const std::string &working_directory,
                const clang::HeaderSearchOptions &header_options) const {
    clang::FileSystemOptions file_options;
    file_options.WorkingDir = working_directory;
    auto diagnostic_options = std::make_shared<clang::DiagnosticOptions>();
    auto diagnostic_ids = llvm::IntrusiveRefCntPtr<clang::DiagnosticIDs>(
        new clang::DiagnosticIDs());
    auto diagnostics = llvm::IntrusiveRefCntPtr<clang::DiagnosticsEngine>(
        new clang::DiagnosticsEngine(diagnostic_ids, *diagnostic_options,
                                     new clang::IgnoringDiagConsumer(), true));
    clang::PCHContainerOperations containers;
#if CLANG_VERSION_MAJOR >= 22
    return clang::ASTUnit::LoadFromASTFile(
        path.string(), containers.getRawReader(),
        clang::ASTUnit::LoadEverything, filesystem, diagnostic_options,
        diagnostics, file_options, header_options);
#else
    return clang::ASTUnit::LoadFromASTFile(
        path.string(), containers.getRawReader(),
        clang::ASTUnit::LoadEverything, diagnostic_options, diagnostics,
        file_options, header_options, nullptr, false,
        clang::CaptureDiagsKind::None, false, false, filesystem);
#endif
  }

  std::unique_ptr<detail::NativeTemporaryArtifact>
  write_artifact(std::string_view bytes) const {
    auto artifact =
        std::make_unique<detail::NativeTemporaryArtifact>("ctk-native-ast");
    std::ofstream output(artifact->path(), std::ios::binary | std::ios::trunc);
    output.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
    if (!output)
      throw std::runtime_error("cannot stage native AST artifact");
    return artifact;
  }

  std::unique_ptr<clang::ASTUnit>
  try_load_stored(const FileInput &file,
                  const ctk::cache::CompilationContext &context,
                  AstSnapshotOwner &owner) const {
    if (!store_ || !context.reusable)
      return {};
    try {
      for (const auto &lease :
           store_->acquire_ready(storage_profile(file, context))) {
        const auto &descriptor = lease->descriptor();
        auto filesystem =
            snapshot::CapturedFileSystem::restore(descriptor.inputs);
        if (!filesystem) {
          try {
            store_->mark_stale(descriptor.id);
          } catch (const std::exception &error) {
            owner.storage_message = error.what();
          }
          continue;
        }
        filesystem->setCurrentWorkingDirectory(context.working_directory);
        bool complete = true;
        for (std::size_t index = 0; index < descriptor.artifacts.size();
             ++index) {
          if (descriptor.artifacts[index].kind ==
              ctk::storage::ArtifactKind::TranslationUnit)
            continue;
          const auto bytes = lease->read_artifact(index);
          if (!filesystem->add_buffer(descriptor.artifacts[index].logical_path,
                                      bytes)) {
            complete = false;
            break;
          }
        }
        if (!complete) {
          store_->mark_stale(descriptor.id);
          continue;
        }
        for (std::size_t index = 0; index < descriptor.artifacts.size();
             ++index) {
          if (descriptor.artifacts[index].kind !=
              ctk::storage::ArtifactKind::TranslationUnit)
            continue;
          try {
            const auto artifact = lease->read_artifact(index);
            auto staged = write_artifact(artifact);
            if (!filesystem->add_buffer(staged->path().string(), artifact))
              throw std::runtime_error(
                  "native root staging could not be captured");
            clang::HeaderSearchOptions header_options;
            for (const auto &input : descriptor.inputs) {
              if (input.role != ctk::storage::InputRole::ModuleInput)
                continue;
              google::protobuf::Struct metadata;
              if (!google::protobuf::util::JsonStringToMessage(
                       input.validation_context, &metadata)
                       .ok())
                throw std::runtime_error("invalid module observation");
              const auto name = metadata.fields().find("module_name");
              if (name != metadata.fields().end() &&
                  !name->second.string_value().empty())
                header_options
                    .PrebuiltModuleFiles[name->second.string_value()] =
                    input.path;
            }
            auto unit =
                load_ast_file(staged->path(), filesystem,
                              context.working_directory, header_options);
            if (!unit) {
              owner.storage_message = "Clang rejected the stored AST artifact";
              try {
                store_->mark_stale(descriptor.id);
              } catch (const std::exception &error) {
                owner.storage_message = error.what();
              }
              break;
            }
            // A readable root must still import the closure that was published.
            // Reject roots with missing imports before lazy declaration access.
            const auto closure = snapshot::capture_native_artifacts(
                *unit, *filesystem, context.working_directory);
            const auto expected_count = std::ranges::count_if(
                descriptor.artifacts, [](const auto &item) {
                  return item.kind !=
                         ctk::storage::ArtifactKind::TranslationUnit;
                });
            if (!closure.reusable || closure.artifacts.size() != expected_count)
              throw std::runtime_error(
                  "stored native root has an incomplete artifact closure");
            for (const auto &expected : descriptor.artifacts) {
              if (expected.kind == ctk::storage::ArtifactKind::TranslationUnit)
                continue;
              const auto found =
                  std::ranges::find(closure.artifacts, expected.logical_path,
                                    &snapshot::NativeArtifact::path);
              if (found == closure.artifacts.end() ||
                  found->kind != expected.kind)
                throw std::runtime_error("stored native root imports disagree "
                                         "with its artifact closure");
            }
            // Staging is owned transport for the TU bytes, not a source
            // freshness input.
            filesystem->exclude_staged(staged->path().string());
            owner.filesystem = std::move(filesystem);
            owner.native_artifact = std::move(staged);
            owner.storage_lease = lease;
            owner.storage_loaded = true;
            return unit;
          } catch (const std::exception &error) {
            owner.storage_message = error.what();
            try {
              store_->mark_stale(descriptor.id);
            } catch (const std::exception &stale_error) {
              owner.storage_message += "; stale marking failed: ";
              owner.storage_message += stale_error.what();
            }
            break;
          }
        }
      }
    } catch (const std::exception &error) {
      owner.storage_message = error.what();
    } catch (...) {
      owner.storage_message = "unknown native AST storage lookup error";
    }
    return {};
  }

  void publish_stored(const FileInput &file,
                      const ctk::cache::CompilationContext &context,
                      AstSnapshotOwner &owner) const {
    if (!store_ || !context.reusable || !owner.reusable ||
        !owner.filesystem->validate())
      return;
    try {
      if (!owner.writer)
        return;
      auto bytes = owner.writer->serialize(owner.unit->getSema());
      ctk::storage::SnapshotDraft draft;
      draft.profile = storage_profile(file, context);
      std::map<std::string, ctk::storage::InputRole> roles;
      for (const auto &artifact : owner.artifact_closure.artifacts)
        roles.emplace(artifact.path,
                      artifact.kind == ctk::storage::ArtifactKind::Module
                          ? ctk::storage::InputRole::ModuleInput
                          : ctk::storage::InputRole::PchInput);
      for (const auto &[path, captured] : owner.filesystem->inputs()) {
        if (captured.staged)
          continue;
        const auto role = path == normalized_path(file)
                              ? ctk::storage::InputRole::MainSource
                          : roles.contains(path) ? roles.at(path)
                          : captured.error || captured.status.isDirectory()
                              ? ctk::storage::InputRole::Lookup
                              : ctk::storage::InputRole::Header;
        auto observation = snapshot::stored_observation(captured, role);
        if (role == ctk::storage::InputRole::ModuleInput) {
          const auto artifact =
              std::ranges::find(owner.artifact_closure.artifacts, path,
                                &snapshot::NativeArtifact::path);
          google::protobuf::Struct metadata;
          if (!google::protobuf::util::JsonStringToMessage(
                   observation.validation_context, &metadata)
                   .ok())
            throw std::runtime_error("invalid module observation");
          (*metadata.mutable_fields())["module_name"].set_string_value(
              artifact->module_name);
          observation.validation_context.clear();
          if (!google::protobuf::util::MessageToJsonString(
                   metadata, &observation.validation_context)
                   .ok())
            throw std::runtime_error("module observation encoding failed");
        }
        draft.inputs.push_back(std::move(observation));
      }
      draft.artifacts.push_back({ctk::storage::ArtifactKind::TranslationUnit,
                                 normalized_path(file), std::move(bytes)});
      for (std::size_t index = 0;
           index < owner.artifact_closure.artifacts.size(); ++index) {
        const auto &artifact = owner.artifact_closure.artifacts[index];
        const auto &captured = owner.filesystem->inputs().at(artifact.path);
        draft.artifacts.push_back(
            {artifact.kind, artifact.path, *captured.bytes});
        draft.dependencies.push_back(
            {0, static_cast<std::uint32_t>(index + 1)});
        for (const auto child : artifact.dependencies)
          draft.dependencies.push_back({static_cast<std::uint32_t>(index + 1),
                                        static_cast<std::uint32_t>(child + 1)});
      }
      if (!owner.filesystem->validate())
        return;
      draft.created_at_ms = 0;
      store_->publish(draft);
    } catch (const std::exception &error) {
      owner.storage_message = error.what();
    } catch (...) {
      owner.storage_message = "unknown AST persistence error";
      // Persistence is optional; a successful native query remains successful.
    }
  }

  std::shared_ptr<ctk::storage::Store> store_;
};

class NativeQueryEngine final : public IQueryEngine {
  class Callback final
      : public clang::ast_matchers::MatchFinder::MatchCallback {
  public:
    Callback(const Checkpoint &checkpoint,
             const IQueryEngine::MatchCallback &callback)
        : checkpoint_(checkpoint), callback_(callback) {}

    void
    run(const clang::ast_matchers::MatchFinder::MatchResult &result) override {
      if (!checkpoint_())
        return;
      Bindings bindings;
      clang::PrintingPolicy policy(result.Context->getLangOpts());
      serialization::SerializationContext context{
          *result.Context, serialization::ProjectionPolicy::Shallow};
      for (const auto &[id, node] : result.Nodes.getMap()) {
        SemanticBinding binding;
        binding.kind = node.getNodeKind().asStringRef().str();
        if (const auto *named = node.get<clang::NamedDecl>())
          binding.name = named->getNameAsString();
        else if (const auto *reference = node.get<clang::DeclRefExpr>())
          binding.name = reference->getDecl()->getNameAsString();
        else if (const auto *member = node.get<clang::MemberExpr>())
          binding.name = member->getMemberDecl()->getNameAsString();
        else if (const auto *call = node.get<clang::CallExpr>()) {
          if (const auto *callee = call->getDirectCallee())
            binding.name = callee->getNameAsString();
        }
        if (const auto *value = node.get<clang::ValueDecl>())
          binding.type = value->getType().getAsString(policy);
        else if (const auto *expression = node.get<clang::Expr>())
          binding.type = expression->getType().getAsString(policy);
        else if (const auto *type = node.get<clang::Type>())
          binding.type = clang::QualType(type, 0).getAsString(policy);
        serialization::NodeSerializerDispatcher::serialize(node, binding.value,
                                                           context);
        bindings.emplace(id, std::move(binding));
      }
      callback_(bindings);
    }

  private:
    const Checkpoint &checkpoint_;
    const IQueryEngine::MatchCallback &callback_;
  };

public:
  NativeQueryEngine()
      : loader_(std::make_shared<ClangSnapshotLoader>(shared_store())),
        cache_(loader_) {}

  ctk::cache::SnapshotPtr acquire_snapshot(const FileInput &file) override {
    const auto resolved = resolve_compilation_command(file);
    return cache_.acquire(normalized_path(resolved), cache_context(resolved));
  }

  ctk::match::v1::CacheResources resources() const override {
    ctk::match::v1::CacheResources result;
    const auto memory = cache_.stats();
    result.set_memory_available(true);
    result.set_reusable_snapshots(memory.reusable_snapshots);
    result.set_reusable_memory_bytes(memory.estimated_reusable_bytes);
    result.set_pending_builds(memory.pending_builds);
    if (const auto store = shared_store()) {
      const auto disk = store->stats();
      result.set_storage_available(true);
      result.set_artifact_disk_bytes(disk.physical_bytes);
      result.set_ready_snapshots(disk.ready_snapshots);
      result.set_stale_snapshots(disk.stale_snapshots);
      result.set_leased_snapshots(disk.leased_snapshots);
      result.set_storage_root(storage_root().string());
    }
    return result;
  }

  void prune_caches(bool memory, bool disk) override {
    if (memory)
      cache_.clear_reuse();
    if (disk)
      if (const auto store = shared_store())
        store->prune_unused();
  }

  QueryResult match(const FileInput &input, const std::string &query,
                    const Checkpoint &checkpoint,
                    const MatchCallback &on_match) override {
    QueryResult result;
    try {
      const auto file = resolve_compilation_command(input);
      auto context = cache_context(file);
      result.profile = context.digest();
      clang::ast_matchers::dynamic::Diagnostics diagnostics;
      llvm::StringRef query_text(query);
      auto matcher =
          clang::ast_matchers::dynamic::Parser::parseMatcherExpression(
              query_text, &diagnostics);
      if (!matcher) {
        result.message = diagnostics.toStringFull();
        return result;
      }
      if (auto root = matcher->tryBind("root"))
        matcher = std::move(root);
      if (!checkpoint()) {
        result.cancelled = true;
        result.message = "query cancelled";
        return result;
      }
      auto snapshot = cache_.acquire(normalized_path(file), context);
      std::unique_lock execution(snapshot->execution_mutex());
      const auto owner =
          std::static_pointer_cast<const AstSnapshotOwner>(snapshot->owner);
      if (!owner || !owner->unit)
        throw std::runtime_error(
            "snapshot cache returned an invalid AST owner");
      retain_snapshot(file, context, snapshot);
      result.snapshot_retained = true;
      result.storage_hit = owner->storage_loaded;
      result.storage_message = owner->storage_message;
      result.native_memory_bytes =
          ast_memory(*owner->unit) + owner->filesystem->estimated_bytes() +
          (owner->writer ? owner->writer->estimated_bytes() : 0);
      if (!checkpoint()) {
        result.cancelled = true;
        result.message = "query cancelled";
      } else {
        Callback callback(checkpoint, on_match);
        clang::ast_matchers::MatchFinder finder;
        if (!finder.addDynamicMatcher(*matcher, &callback)) {
          result.message =
              "matcher is valid but cannot be used as a top-level AST matcher";
        } else {
          finder.matchAST(owner->unit->getASTContext());
          result.cancelled = !checkpoint();
          result.ok = !result.cancelled;
          if (result.cancelled)
            result.message = "query cancelled";
        }
      }
      result.native_memory_bytes =
          ast_memory(*owner->unit) + owner->filesystem->estimated_bytes() +
          (owner->writer ? owner->writer->estimated_bytes() : 0);
    } catch (const std::exception &error) {
      result.message = error.what();
    }
    return result;
  }

private:
  void retain_snapshot(const FileInput &file,
                       const ctk::cache::CompilationContext &context,
                       ctk::cache::SnapshotPtr snapshot) {
    auto stable_context = context;
    stable_context.reusable = true;
    auto key = normalized_path(file);
    key.push_back('\0');
    key += stable_context.canonical_bytes();
    ctk::cache::SnapshotPtr replaced;
    {
      std::lock_guard lock(retained_mutex_);
      auto &retained = retained_snapshots_[std::move(key)];
      replaced = std::exchange(retained, std::move(snapshot));
    }
    // Release old native ownership after dropping the map lock.
    replaced.reset();
  }

  std::shared_ptr<ClangSnapshotLoader> loader_;
  ctk::cache::SnapshotCache cache_;
  std::mutex retained_mutex_;
  std::map<std::string, ctk::cache::SnapshotPtr> retained_snapshots_;
};

} // namespace

std::shared_ptr<IQueryEngine> make_cached_query_engine() {
  return std::make_shared<NativeQueryEngine>();
}

} // namespace ctk::clang_layer
