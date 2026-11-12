#include "script_artifact.hpp"

#include "cpp_source.hpp"
#include "ctk/platform/temporary_directory.hpp"
#include "grammar/lower.hpp"
#include "ir.hpp"
#include "platform/cpp_dependencies.hpp"
#include "platform/launch.hpp"
#include "settings.hpp"

#include <array>
#include <cstdlib>
#include <stdexcept>

#include <openssl/evp.h>
#include <llvm/ADT/StringExtras.h>
#include <llvm/Support/JSON.h>
#include <llvm/Support/Program.h>

namespace ctk::jit {
namespace {

namespace fs = std::filesystem;

constexpr llvm::StringLiteral bundle_magic("CTK-JIT-BUNDLE-1\n");

llvm::Error failure(const llvm::Twine &text) {
  return llvm::createStringError(llvm::inconvertibleErrorCode(), text);
}

llvm::Expected<std::unique_ptr<llvm::MemoryBuffer>> read(const fs::path &path) {
  auto buffer = llvm::MemoryBuffer::getFile(path.string());
  if (!buffer)
    return llvm::createStringError(buffer.getError(), "%s", path.c_str());
  return std::move(*buffer);
}

std::string sha(llvm::StringRef data) {
  std::array<unsigned char, 32> digest;
  unsigned size = 0;
  if (EVP_Digest(data.data(), data.size(), digest.data(), &size, EVP_sha256(),
                 nullptr) != 1 || size != digest.size())
    throw std::runtime_error("SHA-256 calculation failed");
  return llvm::toHex(llvm::ArrayRef(digest), true);
}

std::string json_text(const llvm::json::Value &value) {
  std::string result;
  llvm::raw_string_ostream(result) << value;
  return result;
}

llvm::Expected<std::string> fingerprint(const ScriptToolchain &toolchain) {
  auto executable = read(toolchain.executable);
  if (!executable)
    return executable.takeError();
  auto header = read(toolchain.runtime_header);
  if (!header)
    return header.takeError();
  llvm::json::Array stamps;
  for (const auto &path : toolchain.dependencies) {
    auto identity = dependency_stamp(path);
    if (!identity)
      return identity.takeError();
    stamps.emplace_back(llvm::json::Array{path.string(), std::move(*identity)});
  }
  // The executable identity includes the native parser, lowerer, runtime ABI,
  // target, linked dependency names and the configured compiler flags.
  return sha(json_text(llvm::json::Array{
      sha((*executable)->getBuffer()), sha((*header)->getBuffer()), std::move(stamps)}));
}

fs::path cache_directory() {
  if (const auto *path = std::getenv("CTK_JIT_CACHE_DIR"); path && *path)
    return fs::absolute(path);
  if (auto path = configured_script_cache(); !path.empty())
    return path;
  if (const auto *xdg = std::getenv("XDG_CACHE_HOME"); xdg && *xdg)
    return fs::path(xdg) / "ctk-jit";
  if (const auto *home = std::getenv("HOME"); home && *home)
    return fs::path(home) / ".cache" / "ctk-jit";
  return {};
}

llvm::Expected<ScriptProgram> unpack(llvm::StringRef bytes,
                                     llvm::StringRef toolchain,
                                     llvm::StringRef key = {}) {
  if (!bytes.consume_front(bundle_magic)) {
    if (bytes.starts_with("PK"))
      return failure("bundle was built by the previous ctk-jit; precompile it again");
    return failure("invalid ctk-jit bundle signature");
  }
  const auto [metadata, object] = bytes.split('\n');
  auto decoded = llvm::json::parse(metadata);
  if (!decoded)
    return decoded.takeError();
  const auto *manifest = decoded->getAsObject();
  if (!manifest)
    return failure("invalid ctk-jit bundle manifest");
  if (manifest->getString("toolchain").value_or("") != toolchain)
    return failure("bundle was built for a different ctk-jit toolchain");
  if (!key.empty() && manifest->getString("input_sha256").value_or("") != key)
    return failure("bundle does not match its cache key");
  const auto kind = manifest->getString("kind").value_or("");
  if (kind != "ir-object" && kind != "object")
    return failure("unsupported bundle object kind");
  if (object.empty() || manifest->getString("object_sha256").value_or("") != sha(object))
    return failure("bundle object checksum mismatch");
  return ScriptProgram{llvm::MemoryBuffer::getMemBufferCopy(object), {},
                       kind == "ir-object", true};
}

std::string pack(llvm::StringRef object, bool ir, llvm::StringRef toolchain,
                 llvm::StringRef key) {
  auto result = bundle_magic.str();
  result += json_text(llvm::json::Object{
      {"toolchain", toolchain}, {"input_sha256", key},
      {"kind", ir ? "ir-object" : "object"}, {"object_sha256", sha(object)}});
  result += '\n';
  result += object;
  return result;
}

std::string normalized_source(llvm::StringRef input) {
  std::string source;
  source.reserve(input.size());
  while (!input.empty()) {
    const char byte = input.front();
    input = input.drop_front();
    if (byte == '\r') {
      source += '\n';
      input.consume_front("\n");
    } else {
      source += byte;
    }
  }
  return source;
}

struct SourceFile {
  fs::path path;
  std::string text;
};

llvm::Expected<SourceFile> read_source(const fs::path &path) {
  std::error_code error;
  auto canonical = fs::canonical(path, error);
  if (error)
    return llvm::createStringError(error, "%s", path.c_str());
  auto buffer = read(canonical);
  if (!buffer)
    return buffer.takeError();
  return SourceFile{std::move(canonical), normalized_source((*buffer)->getBuffer())};
}

llvm::Expected<ScriptProgram> lower(const SourceFile &source, bool ir) {
  auto text = ir ? lower_ctk(source.text, false, source.path.string())
                 : cpp_source(source.text, source.path.string(),
                              source.path.extension() == ".ctk");
  if (!text)
    return failure(llvm::Twine(source.path.string()) + ": " +
                   llvm::toString(text.takeError()));
  return ScriptProgram{llvm::MemoryBuffer::getMemBufferCopy(*text),
                       source.path.extension() == ".cpp" ?
                           source.path.parent_path().string() : "",
                       ir, false};
}

llvm::Expected<std::string> clang(const ScriptToolchain &toolchain,
                                  llvm::StringRef source,
                                  llvm::ArrayRef<llvm::StringRef> options,
                                  std::string *diagnostics = nullptr) {
  platform::TemporaryDirectory temporary("ctk-jit-compile");
  const auto input = (temporary.path() / "input").string();
  const auto output = (temporary.path() / "output").string();
  const auto diagnostic = (temporary.path() / "stderr").string();
  if (auto error = write_atomic(input, source))
    return error;
  std::vector<llvm::StringRef> args{toolchain.compiler};
  args.insert(args.end(), toolchain.flags.begin(), toolchain.flags.end());
  args.insert(args.end(), options.begin(), options.end());
  const std::array<std::optional<llvm::StringRef>, 3> redirects{input, output, diagnostic};
  std::string launch_error;
  const auto status = llvm::sys::ExecuteAndWait(toolchain.compiler, args, std::nullopt,
                                                 redirects, 0, 0, &launch_error);
  if (status != 0 || diagnostics) {
    auto error = read(diagnostic);
    if (!error) {
      llvm::consumeError(error.takeError());
    } else if (status != 0 && !(*error)->getBuffer().trim().empty()) {
      return failure((*error)->getBuffer().trim());
    } else if (diagnostics) {
      *diagnostics = (*error)->getBuffer().str();
    }
  }
  if (status != 0)
    return failure(launch_error.empty() ? "Clang compilation failed" : launch_error);
  auto data = read(output);
  if (!data)
    return data.takeError();
  return (*data)->getBuffer().str();
}

llvm::Expected<std::string> preprocess(const ScriptProgram &program,
                                       const ScriptToolchain &toolchain,
                                       std::optional<llvm::json::Object> *observed) {
  std::vector<llvm::StringRef> args{"-E", "-x", "c++", "-"};
  if (!program.quote_directory.empty()) {
    args.emplace_back("-iquote");
    args.emplace_back(program.quote_directory);
  }
  if (!observed)
    return clang(toolchain, program.input->getBuffer(), args);
  platform::TemporaryDirectory temporary("ctk-jit-deps");
  const auto depfile = (temporary.path() / "includes.d").string();
  args.insert(args.end(), {"-MD", "-MF", depfile, "-MT", "ctk-jit", "-v", "-Wdate-time"});
  std::string diagnostics;
  const auto started = std::chrono::system_clock::now();
  auto output = clang(toolchain, program.input->getBuffer(), args, &diagnostics);
  if (!output)
    return output.takeError();
  auto deps = read(depfile);
  if (deps)
    *observed = observe_cpp_dependencies((*deps)->getBuffer(), diagnostics, started);
  else
    llvm::consumeError(deps.takeError());
  return output;
}

fs::path artifact_path(const fs::path &cache, bool ir, llvm::StringRef toolchain,
                        llvm::StringRef key) {
  return cache / ((ir ? "ir-obj-" : "obj-") + toolchain.str() + "-" + key.str() + ".bundle");
}

std::optional<std::string> cached_object(const fs::path &cache, bool ir,
                                          llvm::StringRef toolchain,
                                          llvm::StringRef key) {
  auto contents = read(artifact_path(cache, ir, toolchain, key));
  if (!contents) {
    llvm::consumeError(contents.takeError());
    return std::nullopt;
  }
  auto checked = unpack((*contents)->getBuffer(), toolchain, key);
  if (!checked) {
    llvm::consumeError(checked.takeError());
    return std::nullopt;
  }
  if (checked->llvm_ir != ir)
    return std::nullopt;
  return (*contents)->getBuffer().str();
}

fs::path cpp_index(const SourceFile &source, const fs::path &cache,
                   llvm::StringRef toolchain_key, const ScriptToolchain &toolchain) {
  std::string plan;
  auto result = clang(toolchain, "", {"-E", "-x", "c++", "-", "-###"}, &plan);
  if (!result) {
    llvm::consumeError(result.takeError());
    return {};
  }
  const llvm::StringRef options(plan);
  if (!options.contains("\"-cc1\"") || options.contains("\"-ivfsoverlay\"") ||
      options.contains("\"-vfsoverlay\"") || options.contains("\"-fmodules\""))
    return {};
  const auto key = sha(json_text(llvm::json::Array{
      source.path.string(), sha(source.text), toolchain_key, sha(plan)}));
  return cache / ("script-" + key + ".json");
}

std::optional<std::string> cached_cpp_script(const fs::path &index, const fs::path &cache,
                                             llvm::StringRef toolchain_key) {
  auto contents = read(index);
  if (!contents) {
    llvm::consumeError(contents.takeError());
    return std::nullopt;
  }
  auto decoded = llvm::json::parse((*contents)->getBuffer());
  if (!decoded) {
    llvm::consumeError(decoded.takeError());
    return std::nullopt;
  }
  const auto *record = decoded->getAsObject();
  if (!record)
    return std::nullopt;
  const auto key = record->getString("input_sha256").value_or("");
  const auto *observed = record->getObject("observations");
  if (!observed || key.size() != 64 ||
      !llvm::all_of(key, [](char ch) { return llvm::isHexDigit(ch); }) ||
      !cpp_dependencies_unchanged(*observed))
    return std::nullopt;
  return cached_object(cache, false, toolchain_key, key);
}

llvm::Expected<std::string> build_bundle(const SourceFile &source, bool ir,
                                         const fs::path &cache,
                                         llvm::StringRef toolchain_key,
                                         const ScriptToolchain &toolchain) {
  std::string key;
  std::string cpp_snapshot;
  fs::path index;
  std::optional<llvm::json::Object> observed;
  if (ir) {
    key = sha(json_text(llvm::json::Array{source.path.string(), sha(source.text)}));
  } else {
    if (!cache.empty() && source.path.extension() == ".ctk") {
      index = cpp_index(source, cache, toolchain_key, toolchain);
      if (!index.empty())
        if (auto cached = cached_cpp_script(index, cache, toolchain_key))
          return std::move(*cached);
    }
    auto program = lower(source, false);
    if (!program)
      return program.takeError();
    auto frozen = preprocess(*program, toolchain, index.empty() ? nullptr : &observed);
    if (!frozen)
      return frozen.takeError();
    cpp_snapshot = std::move(*frozen);
    key = sha(cpp_snapshot);
  }

  const auto publish_index = [&] {
    if (observed)
      llvm::consumeError(write_atomic(index, json_text(llvm::json::Object{
          {"input_sha256", key}, {"observations", std::move(*observed)}})));
  };
  if (!cache.empty()) {
    if (auto cached = cached_object(cache, ir, toolchain_key, key)) {
      publish_index();
      return std::move(*cached);
    }
  }

  std::string object;
  if (ir) {
    auto program = lower(source, true);
    if (!program)
      return program.takeError();
    auto compiled = compile_ir_object(program->input->getBuffer());
    if (!compiled)
      return compiled.takeError();
    object = (*compiled)->getBuffer().str();
  } else {
    auto compiled = clang(toolchain, cpp_snapshot,
                          {"-x", "c++-cpp-output", "-c", "-", "-o", "-"});
    if (!compiled)
      return compiled.takeError();
    object = std::move(*compiled);
  }

  auto bundle = pack(object, ir, toolchain_key, key);
  if (!cache.empty()) {
    if (auto error = write_atomic(artifact_path(cache, ir, toolchain_key, key), bundle))
      llvm::consumeError(std::move(error));
    else
      publish_index();
  }
  return bundle;
}

} // namespace

llvm::Expected<ScriptProgram> script_program(const fs::path &script, bool ir,
                                            bool no_cache,
                                            const ScriptToolchain &toolchain) {
  auto source = read_source(script);
  if (!source)
    return source.takeError();
  if (!no_cache && source->path.extension() == ".ctk") {
    const auto cache = cache_directory();
    if (prepare_private_cache(cache)) {
      auto key = fingerprint(toolchain);
      if (key) {
        auto bundle = build_bundle(*source, ir, cache, *key, toolchain);
        if (!bundle)
          return bundle.takeError();
        return unpack(*bundle, *key);
      }
      llvm::consumeError(key.takeError());
    }
  }
  return lower(*source, ir);
}

llvm::Error precompile_script(const fs::path &script, const fs::path &output,
                              bool ir, bool no_cache,
                              const ScriptToolchain &toolchain) {
  auto source = read_source(script);
  if (!source)
    return source.takeError();
  if (fs::weakly_canonical(output) == source->path)
    return failure("bundle output must differ from the source script");
  auto key = fingerprint(toolchain);
  if (!key)
    return key.takeError();
  const auto cache = no_cache ? fs::path{} : cache_directory();
  auto bundle = build_bundle(*source, ir, prepare_private_cache(cache) ? cache : fs::path{},
                             *key, toolchain);
  if (!bundle)
    return bundle.takeError();
  return write_atomic(output, *bundle);
}

llvm::Expected<ScriptProgram> read_script_bundle(
    const fs::path &path, const ScriptToolchain &toolchain) {
  auto contents = read(path);
  if (!contents)
    return contents.takeError();
  auto key = fingerprint(toolchain);
  if (!key)
    return key.takeError();
  return unpack((*contents)->getBuffer(), *key);
}

} // namespace ctk::jit
