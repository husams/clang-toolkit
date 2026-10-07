#include "native_artifact_closure.hpp"
#include <clang/Lex/PreprocessingRecord.h>
#include <clang/Lex/Preprocessor.h>
#include <clang/Serialization/ASTReader.h>
#include <clang/Serialization/ModuleFile.h>
#include <filesystem>
#include <llvm/Support/xxhash.h>
namespace ctk::clang_layer::snapshot {
NativeArtifactClosure
capture_native_artifacts(clang::ASTUnit &unit, CapturedFileSystem &filesystem,
                         const std::string &working_directory) {
  NativeArtifactClosure result;
  auto reader = unit.getASTReader();
  if (!reader)
    return result;
  std::map<const clang::serialization::ModuleFile *, std::size_t> indexes;
  auto absolute = [&](const std::string &name) {
    auto path = std::filesystem::path(name);
    if (path.is_relative())
      path = std::filesystem::path(working_directory) / path;
    return path.string();
  };
  for (auto &module : reader->getModuleManager()) {
    if (module.Kind == clang::serialization::MK_MainFile)
      continue;
    if (!module.Buffer) {
      result.reusable = false;
      continue;
    }
    const auto path = absolute(module.FileName);
    if (!filesystem.add_buffer(path, module.Buffer->getBuffer())) {
      result.reusable = false;
      continue;
    }
    indexes.emplace(&module, result.artifacts.size());
    result.artifacts.push_back(
        {module.isModule() ? ctk::storage::ArtifactKind::Module
                           : ctk::storage::ArtifactKind::Pch,
         std::filesystem::path(path).lexically_normal().string(),
         module.ModuleName,
         {}});
    std::vector<clang::serialization::InputFileInfo> infos;
    reader->visitInputFileInfos(
        module, true, [&](const auto &info, bool) { infos.push_back(info); });
    std::size_t index = 0;
    reader->visitInputFiles(module, true, true, [&](const auto &input, bool) {
      if (index >= infos.size()) {
        result.reusable = false;
        return;
      }
      const auto &info = infos[index++];
      const auto file = input.getFile();
      if (!file || input.isNotFound() || input.isOutOfDate() ||
          info.Transient || info.Overridden) {
        result.reusable = false;
        return;
      }
      auto buffer = unit.getFileManager().getBufferForFile(*file);
      if (!buffer || !filesystem.add_buffer(absolute(file->getName().str()),
                                            (*buffer)->getBuffer())) {
        result.reusable = false;
        return;
      }
      if (!info.ContentHash) {
        result.reusable = false;
        return;
      }
      if (info.ContentHash != llvm::xxh3_64bits((*buffer)->getBuffer()))
        throw std::runtime_error("native precompiled input content differs "
                                 "from its compiled artifact: " +
                                 file->getName().str());
    });
    if (index != infos.size())
      result.reusable = false;
  }
  for (const auto &[module, index] : indexes)
    for (const auto *import : module->Imports) {
      if (auto found = indexes.find(import); found != indexes.end())
        result.artifacts[index].dependencies.push_back(found->second);
      else
        result.reusable = false;
    }
  // Load source buffers referenced by lazy native file entries before sealing.
  auto &manager = unit.getSourceManager();
  for (unsigned index = 0; index < manager.loaded_sloc_entry_size(); ++index) {
    bool invalid = false;
    const auto &entry = manager.getLoadedSLocEntry(index, &invalid);
    if (invalid) {
      result.reusable = false;
      continue;
    }
    if (entry.isFile()) {
      if (!entry.getFile().getContentCache().getBufferOrNone(
              unit.getDiagnostics(), unit.getFileManager()))
        result.reusable = false;
    }
  }
  return result;
}
} // namespace ctk::clang_layer::snapshot
