#pragma once
#include "ctk/clang/project_index_extract.hpp"
#include "index/v1/index_service.pb.h"
#include <algorithm>
#include <array>
#include <clang/Frontend/CompilerInstance.h>
#include <clang/Lex/Lexer.h>
#include <clang/Lex/LiteralSupport.h>
#include <clang/Lex/MacroInfo.h>
#include <clang/Lex/PPCallbacks.h>
#include <clang/Lex/Preprocessor.h>
#include <clang/Lex/PreprocessorOptions.h>
#include <clang/Serialization/ASTReader.h>
#include <filesystem>
#include <fstream>
#include <llvm/Support/FileSystem.h>
#include <llvm/Support/SHA256.h>
#include <llvm/Support/raw_ostream.h>

namespace ctk::clang_layer {
// Reuse extraction, never the native AST. An exact preprocessed/context match
// is deliberately conservative; unsupported contexts take normal traversal.
class HeaderDefinitionReuse {
public:
  HeaderDefinitionReuse(clang::CompilerInstance &compiler,
                        ProjectIndexExtraction &result, std::string directory,
                        bool enabled)
      : compiler_(compiler), result_(result), directory_(std::move(directory)),
        eligible_(enabled && !directory_.empty()) {
    const auto &invocation = compiler_.getInvocation();
    const auto &preprocessing = invocation.getPreprocessorOpts();
    const auto &frontend = compiler_.getFrontendOpts();
    eligible_ =
        eligible_ && preprocessing.ImplicitPCHInclude.empty() &&
        preprocessing.Includes.empty() && preprocessing.MacroIncludes.empty() &&
        preprocessing.ChainedIncludes.empty() &&
        frontend.ASTMergeFiles.empty() && frontend.Plugins.empty() &&
        frontend.AddPluginActions.empty() && frontend.ModuleFiles.empty();
    add(result_.compile_context);
    bool skip_value = false;
    const auto source = compiler_.getFrontendOpts().Inputs.front().getFile();
    compiler_.getInvocation().generateCC1CommandLine(
        [&](const llvm::Twine &arg) {
          const auto value = arg.str();
          if (skip_value) {
            skip_value = false;
            return;
          }
          if (value == "-main-file-name" || value == "-o") {
            skip_value = true;
            return;
          }
          if (value != source) {
            add(value);
          }
        });
  }
  void file_changed(clang::SourceLocation,
                    clang::PPCallbacks::FileChangeReason reason,
                    clang::SrcMgr::CharacteristicKind, clang::FileID previous) {
    if (reason == clang::PPCallbacks::SystemHeaderPragma)
      diagnostic_pragma();
    flush_pragma();
    if (!eligible_ || reason != clang::PPCallbacks::ExitFile ||
        previous.isInvalid())
      return;
    auto &sm = compiler_.getSourceManager();
    if (previous == sm.getMainFileID() ||
        sm.getIncludeLoc(previous).isInvalid() ||
        sm.isInSystemHeader(sm.getLocForStartOfFile(previous)))
      return;
    // Snapshot the complete preceding semantic token context, including nested
    // includes, and bind this header's exact physical file and directives.
    const auto identity = file_identity(previous);
    if (!eligible_)
      return;
    auto snapshot = hash_;
    snapshot.update(identity);
    entries_[previous].key =
        llvm::toHex(llvm::ArrayRef<uint8_t>(snapshot.final()), true);
  }
  void token(const clang::Token &token) {
    flush_pragma();
    if (!eligible_ || token.is(clang::tok::eof))
      return;
    if (token.isAnnotation())
      return; // Parser annotations are not new input tokens.
    if (token.getLocation().isInvalid())
      return;
    if (token.is(clang::tok::raw_identifier)) {
      eligible_ = false;
      return;
    }
    auto &sm = compiler_.getSourceManager();
    const auto spelling = sm.getSpellingLoc(token.getLocation());
    const auto expansion = sm.getExpansionLoc(token.getLocation());
    const auto spelling_id = sm.getFileID(spelling),
               expansion_id = sm.getFileID(expansion);
    const auto spelling_identity = file_identity(spelling_id);
    const auto expansion_identity = file_identity(expansion_id);
    if (!eligible_)
      return;
    if (last_spelling_ != spelling_identity) {
      add("spelling");
      hash_.update(spelling_identity);
      last_spelling_ = spelling_identity;
    }
    if (last_expansion_ != expansion_identity) {
      add("expansion");
      hash_.update(expansion_identity);
      last_expansion_ = expansion_identity;
    }
    const std::uint32_t provenance[] = {
        static_cast<std::uint32_t>(token.getKind()), sm.getFileOffset(spelling),
        sm.getFileOffset(expansion)};
    hash_.update(llvm::ArrayRef<uint8_t>(
        reinterpret_cast<const uint8_t *>(provenance), sizeof(provenance)));
    if (const auto *identifier = token.getIdentifierInfo())
      add(identifier->getName());
    else if (token.isLiteral())
      add(llvm::StringRef(token.getLiteralData(), token.getLength()));
  }
  void macro(const clang::Token &token,
             const clang::MacroDefinition &definition) {
    const auto *info = definition.getMacroInfo();
    const auto *identifier = token.getIdentifierInfo();
    if (!info || !info->isBuiltinMacro() || !identifier)
      return;
    const auto name = identifier->getName();
    if (name == "__BASE_FILE__" || name == "__DATE__" || name == "__TIME__" ||
        name == "__TIMESTAMP__")
      eligible_ = false;
  }
  void pragma(clang::SourceLocation location,
              clang::PragmaIntroducerKind kind) {
    flush_pragma();
    pending_pragma_ = location;
    pending_pragma_kind_ = kind;
  }
  void diagnostic_pragma() { pending_pragma_ = {}; }
  void semantic_pragma(llvm::StringRef value) {
    pending_pragma_ = {};
    if (eligible_)
      add(value);
  }
  void prepare() {
    flush_pragma();
    if (compiler_.getDiagnostics().hasErrorOccurred() ||
        (compiler_.getASTReader() &&
         compiler_.getASTReader()->getModuleManager().size() != 0)) {
      entries_.clear();
      return;
    }
    for (auto &[file, entry] : entries_) {
      if (entry.key.empty())
        continue;
      load_entry(entry);
    }
  }
  struct Entry {
    std::string key;
    std::filesystem::path path;
    bool hit = false;
    std::uint64_t bytes = 0;
    std::vector<IndexedSymbol> symbols;
  };
  void load_entry(Entry &entry) {
    try {
      entry.path =
          std::filesystem::path(directory_) / (entry.key + ".definitions");
      if (!std::filesystem::is_regular_file(entry.path))
        return;
      const auto size = std::filesystem::file_size(entry.path);
      if (size < 65 || size > max_bytes ||
          cache_bytes_ + size > max_cache_bytes)
        return;
      std::ifstream input(entry.path, std::ios::binary);
      std::string checksum(64, '\0');
      input.read(checksum.data(), 64);
      if (!input || input.get() != '\n')
        return;
      std::string payload(size - 65, '\0');
      input.read(payload.data(), payload.size());
      if (input.gcount() != static_cast<std::streamsize>(payload.size()) ||
          input.peek() != std::char_traits<char>::eof())
        return;
      llvm::SHA256 digest;
      digest.update(payload);
      if (checksum !=
          llvm::toHex(llvm::ArrayRef<uint8_t>(digest.final()), true))
        return;
      ctk::index::v1::IndexWorkerResponse cached;
      if (!cached.ParseFromString(payload) || !cached.success() ||
          cached.compile_context() != entry.key)
        return;
      for (const auto &symbol : cached.symbols())
        if (!symbol.is_definition() || symbol.usr().empty() ||
            symbol.file_path().empty())
          return;
      std::uint64_t bytes = 0;
      for (const auto &symbol : cached.symbols())
        bytes += symbol.usr().size() + symbol.name().size() +
                 symbol.qualified_name().size() + symbol.kind().size() +
                 symbol.file_path().size() + symbol.signature().size() + 256;
      if (cache_bytes_ + bytes > max_cache_bytes)
        return;
      for (const auto &symbol : cached.symbols())
        entry.symbols.push_back(
            {symbol.usr(), symbol.name(), symbol.qualified_name(),
             symbol.kind(), symbol.file_path(), symbol.signature(),
             symbol.line(), symbol.column(), symbol.byte_offset(), true});
      entry.bytes = bytes;
      cache_bytes_ += bytes;
      std::error_code ignored;
      std::filesystem::last_write_time(
          entry.path, std::filesystem::file_time_type::clock::now(), ignored);
      entry.hit = true;
    } catch (...) {
      entry.symbols.clear();
      // A cache is optional: corruption or I/O errors must not lose
      // definitions.
    }
  }
  bool skip(const clang::Decl *decl) const {
    if (!decl || decl->getLocation().isInvalid())
      return false;
    const auto file = compiler_.getSourceManager().getFileID(
        compiler_.getSourceManager().getExpansionLoc(decl->getLocation()));
    const auto found = entries_.find(file);
    return found != entries_.end() && found->second.hit &&
           complete_in_file(decl, file);
  }
  void record(const clang::Decl *decl, const IndexedSymbol &symbol) {
    if (decl->getLocation().isInvalid())
      return;
    const auto file = compiler_.getSourceManager().getFileID(
        compiler_.getSourceManager().getExpansionLoc(decl->getLocation()));
    if (!complete_in_file(decl, file))
      return;
    auto found = entries_.find(file);
    if (found == entries_.end() || found->second.hit ||
        found->second.key.empty())
      return;
    auto &entry = found->second;
    const auto bytes = symbol.usr.size() + symbol.name.size() +
                       symbol.qualified_name.size() + symbol.kind.size() +
                       symbol.file_path.size() + symbol.signature.size() + 256;
    if (entry.bytes + bytes < max_bytes &&
        cache_bytes_ + bytes < max_cache_bytes) {
      entry.bytes += bytes;
      cache_bytes_ += bytes;
      entry.symbols.push_back(symbol);
    } else {
      cache_bytes_ -= entry.bytes;
      entry.bytes = 0;
      entry.symbols.clear();
      entry.key.clear();
    }
  }
  template <class Include> void finish(Include &&include) {
    if (compiler_.getDiagnostics().hasErrorOccurred())
      return;
    std::vector<const Entry *> pending;
    for (auto &[file, entry] : entries_) {
      if (entry.hit) {
        for (const auto &symbol : entry.symbols)
          if (include(symbol)) {
            ++result_.reused_header_symbols;
            result_.symbols.push_back(symbol);
          }
      } else if (!entry.key.empty() && !entry.symbols.empty())
        pending.push_back(&entry);
    }
    // Prefer expensive headers; avoid writing hundreds of tiny fragments per
    // TU.
    std::sort(pending.begin(), pending.end(),
              [](const auto *a, const auto *b) { return a->bytes > b->bytes; });
    for (std::size_t i = 0; i < std::min<std::size_t>(8, pending.size()); ++i)
      save_entry(*pending[i]);
  }
  void save_entry(const Entry &entry) {
    try {
      ctk::index::v1::IndexWorkerResponse cached;
      cached.set_success(true);
      cached.set_compile_context(entry.key);
      for (const auto &symbol : entry.symbols) {
        auto *entry = cached.add_symbols();
        entry->set_usr(symbol.usr);
        entry->set_name(symbol.name);
        entry->set_qualified_name(symbol.qualified_name);
        entry->set_kind(symbol.kind);
        entry->set_file_path(symbol.file_path);
        entry->set_signature(symbol.signature);
        entry->set_line(symbol.line);
        entry->set_column(symbol.column);
        entry->set_byte_offset(symbol.byte_offset);
        entry->set_is_definition(true);
      }
      const auto payload = cached.SerializeAsString();
      if (payload.size() + 65 > max_bytes)
        return;
      std::filesystem::create_directories(directory_);
      std::vector<std::filesystem::directory_entry> entries;
      std::uint64_t disk_bytes = 0;
      for (const auto &entry : std::filesystem::directory_iterator(directory_))
        if (entry.is_regular_file() &&
            entry.path().extension() == ".definitions") {
          entries.push_back(entry);
          disk_bytes += entry.file_size();
        }
      std::sort(entries.begin(), entries.end(),
                [](const auto &a, const auto &b) {
                  return a.last_write_time() < b.last_write_time();
                });
      std::size_t retained = entries.size();
      for (const auto &existing : entries) {
        if (retained < max_entries &&
            disk_bytes + payload.size() + 65 <= max_disk_bytes)
          break;
        disk_bytes -= existing.file_size();
        std::filesystem::remove(existing);
        --retained;
      }
      llvm::SHA256 digest;
      digest.update(payload);
      llvm::SmallString<256> temporary;
      int descriptor = -1;
      if (llvm::sys::fs::createUniqueFile(entry.path.string() + ".%%%%%%.tmp",
                                          descriptor, temporary))
        return;
      {
        llvm::raw_fd_ostream output(descriptor, true);
        output << llvm::toHex(llvm::ArrayRef<uint8_t>(digest.final()), true)
               << '\n'
               << payload;
        output.close();
        if (output.has_error()) {
          std::filesystem::remove(temporary.str().str());
          return;
        }
      }
      std::error_code error;
      std::filesystem::rename(temporary.str().str(), entry.path, error);
      if (error)
        std::filesystem::remove(temporary.str().str());
    } catch (...) {
    }
  }

private:
  bool complete_in_file(const clang::Decl *decl, clang::FileID file) const {
    auto &sm = compiler_.getSourceManager();
    // Includes can end halfway through a declaration or its lexical context.
    // Such declarations must be extracted from the completed current AST.
    for (const auto *current = decl; current;) {
      if (llvm::isa<clang::TranslationUnitDecl>(current))
        break;
      if (current->getBeginLoc().isInvalid() ||
          current->getEndLoc().isInvalid() ||
          sm.getFileID(sm.getExpansionLoc(current->getBeginLoc())) != file ||
          sm.getFileID(sm.getExpansionLoc(current->getEndLoc())) != file)
        return false;
      const auto *parent = current->getLexicalDeclContext();
      current = parent ? clang::Decl::castFromDeclContext(parent) : nullptr;
    }
    return true;
  }
  void add(llvm::StringRef value) {
    hash_.update(std::to_string(value.size()));
    hash_.update(":");
    hash_.update(value);
  }
  std::array<uint8_t, 32> file_identity(clang::FileID file) {
    if (auto found = identities_.find(file); found != identities_.end())
      return found->second;
    auto &sm = compiler_.getSourceManager();
    const auto name = sm.getFilename(sm.getLocForStartOfFile(file));
    bool invalid = false;
    const auto buffer = sm.getBufferData(file, &invalid);
    if (invalid) {
      eligible_ = false;
      return {};
    }
    std::error_code error;
    const auto physical =
        name.empty() || name.starts_with("<")
            ? name.str()
            : std::filesystem::weakly_canonical(name.str(), error).string();
    if (error) {
      eligible_ = false;
      return {};
    }
    llvm::SHA256 identity;
    identity.update(physical);
    identity.update(buffer);
    const auto value = identity.final();
    identities_.emplace(file, value);
    return value;
  }
  void flush_pragma() {
    if (!eligible_ || pending_pragma_.isInvalid())
      return;
    auto &sm = compiler_.getSourceManager();
    const auto location = sm.getSpellingLoc(pending_pragma_);
    const auto data = sm.getBufferData(sm.getFileID(location));
    const auto offset = sm.getFileOffset(location);
    const auto start = data.rfind('\n', offset);
    auto line = data.substr(start == llvm::StringRef::npos ? 0 : start + 1)
                    .split('\n')
                    .first.trim();
    std::string decoded;
    if (pending_pragma_kind_ == clang::PIK__Pragma) {
      auto cursor = location;
      clang::Token raw;
      bool valid = true;
      for (auto expected : {clang::tok::identifier, clang::tok::l_paren,
                            clang::tok::string_literal}) {
        if (clang::Lexer::getRawToken(cursor, raw, sm, compiler_.getLangOpts(),
                                      true) ||
            (expected == clang::tok::identifier
                 ? !raw.is(clang::tok::raw_identifier)
                 : !raw.is(expected))) {
          valid = false;
          break;
        }
        cursor = clang::Lexer::getLocForEndOfToken(raw.getLocation(), 0, sm,
                                                   compiler_.getLangOpts());
      }
      if (valid) {
        clang::StringLiteralParser literal(raw, compiler_.getPreprocessor());
        if (!literal.hadError) {
          decoded = literal.GetString().str();
          line = decoded;
        }
      }
    }
    line.consume_front("#");
    line = line.ltrim();
    line.consume_front("pragma");
    line = line.ltrim();
    if (line == "GCC visibility push(default)" ||
        line == "GCC visibility push(hidden)" ||
        line == "GCC visibility push(protected)" ||
        line == "GCC visibility push(internal)" ||
        line == "GCC visibility pop") {
      add(line);
      pending_pragma_ = {};
      return;
    }
    // Loop unroll hints affect code generation, not definition identity/type.
    const bool unroll_hint =
        line == "unroll" ||
        (line.starts_with("unroll ") && !line.drop_front(7).empty() &&
         std::all_of(line.begin() + 7, line.end(),
                     [](char c) { return c >= '0' && c <= '9'; }));
    // once only affects whether tokens are emitted; diagnostic pragmas are
    // cleared by dedicated callbacks. Other pragmas can alter native AST state.
    if (!unroll_hint && line != "once" && !line.starts_with("once //") &&
        !line.starts_with("once /*") && !line.starts_with("push_macro(") &&
        !line.starts_with("pop_macro(") &&
        !line.starts_with("clang deprecated("))
      eligible_ = false;
    pending_pragma_ = {};
  }
  static constexpr std::uint64_t max_bytes = 32 * 1024 * 1024;
  static constexpr std::size_t max_entries = 4096;
  static constexpr std::uint64_t max_disk_bytes = 512 * 1024 * 1024;
  static constexpr std::uint64_t max_cache_bytes = 64 * 1024 * 1024;
  std::uint64_t cache_bytes_ = 0;
  clang::CompilerInstance &compiler_;
  ProjectIndexExtraction &result_;
  std::string directory_;
  llvm::SHA256 hash_;
  std::map<clang::FileID, Entry> entries_;
  std::map<clang::FileID, std::array<uint8_t, 32>> identities_;
  std::array<uint8_t, 32> last_spelling_{}, last_expansion_{};
  clang::SourceLocation pending_pragma_;
  clang::PragmaIntroducerKind pending_pragma_kind_ = clang::PIK_HashPragma;
  bool eligible_;
};
class HeaderReuseCallbacks final : public clang::PPCallbacks {
public:
  explicit HeaderReuseCallbacks(HeaderDefinitionReuse &reuse) : reuse_(reuse) {}
  void FileChanged(clang::SourceLocation location, FileChangeReason reason,
                   clang::SrcMgr::CharacteristicKind type,
                   clang::FileID previous) override {
    reuse_.file_changed(location, reason, type, previous);
  }
  void MacroExpands(const clang::Token &token,
                    const clang::MacroDefinition &definition,
                    clang::SourceRange, const clang::MacroArgs *) override {
    reuse_.macro(token, definition);
  }

  void PragmaDirective(clang::SourceLocation location,
                       clang::PragmaIntroducerKind kind) override {
    reuse_.pragma(location, kind);
  }
  void PragmaDiagnosticPush(clang::SourceLocation, llvm::StringRef) override {
    reuse_.diagnostic_pragma();
  }
  void PragmaDiagnosticPop(clang::SourceLocation, llvm::StringRef) override {
    reuse_.diagnostic_pragma();
  }
  void PragmaDiagnostic(clang::SourceLocation, llvm::StringRef,
                        clang::diag::Severity, llvm::StringRef) override {
    reuse_.diagnostic_pragma();
  }

  void PragmaAssumeNonNullBegin(clang::SourceLocation) override {
    reuse_.semantic_pragma("assume_nonnull begin");
  }
  void PragmaAssumeNonNullEnd(clang::SourceLocation) override {
    reuse_.semantic_pragma("assume_nonnull end");
  }

private:
  HeaderDefinitionReuse &reuse_;
};
} // namespace ctk::clang_layer
