#include "captured_filesystem.hpp"
#include "captured_directory.hpp"
#include "captured_file.hpp"
#include "ctk/cache/path_policy.hpp"
#include "input_identity.hpp"
#include <algorithm>
#include <filesystem>
#include <google/protobuf/struct.pb.h>
#include <google/protobuf/util/json_util.h>
namespace ctk::clang_layer::snapshot {
CapturedFileSystem::CapturedFileSystem(
    llvm::IntrusiveRefCntPtr<llvm::vfs::FileSystem> underlying)
    : ProxyFileSystem(std::move(underlying)) {}
llvm::IntrusiveRefCntPtr<CapturedFileSystem> CapturedFileSystem::physical() {
  return llvm::makeIntrusiveRefCnt<CapturedFileSystem>(
      llvm::IntrusiveRefCntPtr<llvm::vfs::FileSystem>(
          llvm::vfs::createPhysicalFileSystem().release()));
}
std::string CapturedFileSystem::absolute_lookup(const llvm::Twine &path) const {
  auto input = std::filesystem::path(path.str());
  if (input.is_relative()) {
    auto cwd = getUnderlyingFS().getCurrentWorkingDirectory();
    if (!cwd)
      throw std::runtime_error("filesystem working directory unavailable");
    input = std::filesystem::path(*cwd) / input;
  }
  return input.string();
}
std::string CapturedFileSystem::key(const llvm::Twine &path) const {
  return ctk::cache::path_key(
      std::filesystem::path(absolute_lookup(path)).lexically_normal().string());
}
CapturedInput *CapturedFileSystem::capture(const llvm::Twine &path) {
  const auto name = key(path);
  if (auto found = inputs_.find(name); found != inputs_.end()) {
    auto &input = found->second;
    const auto spelling = absolute_lookup(path);
    if (spelling == input.lookup_path ||
        std::ranges::find(input.aliases, spelling) != input.aliases.end())
      return &input;
    if (sealed_ || input.aliases.size() >= max_inputs) {
      complete_ = false;
      return nullptr;
    }
    auto metadata = getUnderlyingFS().status(spelling);
    llvm::SmallString<256> real;
    if ((!metadata && metadata.getError() != input.error) ||
        (metadata &&
         (input.error || metadata->getType() != input.status.getType() ||
          getUnderlyingFS().getRealPath(spelling, real) ||
          real.str() != input.real_path))) {
      complete_ = false;
      return nullptr;
    }
    input.aliases.push_back(spelling);
    return &input;
  }
  if (sealed_) {
    complete_ = false;
    return nullptr;
  }
  if (inputs_.size() >= max_inputs) {
    complete_ = false;
    return nullptr;
  }
  CapturedInput input;
  input.path = name;
  input.lookup_path = absolute_lookup(path);
  auto metadata = getUnderlyingFS().status(input.lookup_path);
  if (!metadata)
    input.error = metadata.getError();
  else {
    input.status = *metadata;
    llvm::SmallString<256> real;
    if (getUnderlyingFS().getRealPath(input.lookup_path, real)) {
      complete_ = false;
    } else
      input.real_path = real.str().str();
    if (metadata->isRegularFile()) {
      if (metadata->getSize() > max_bytes - bytes_) {
        complete_ = false;
        return nullptr;
      }
      auto buffer = getUnderlyingFS().getBufferForFile(input.lookup_path, -1,
                                                       true, true, false);
      if (!buffer) {
        complete_ = false;
        return nullptr;
      }
      if ((*buffer)->getBufferSize() > max_bytes - bytes_) {
        complete_ = false;
        return nullptr;
      }
      input.bytes =
          std::make_shared<const std::string>((*buffer)->getBuffer().str());
      bytes_ += input.bytes->size();
      input.status =
          llvm::vfs::Status::copyWithNewSize(input.status, input.bytes->size());
    } else if (!metadata->isDirectory()) {
      complete_ = false;
      return nullptr;
    }
  }
  return &inputs_.emplace(name, std::move(input)).first->second;
}
llvm::ErrorOr<llvm::vfs::Status>
CapturedFileSystem::status(const llvm::Twine &path) {
  auto *input = capture(path);
  if (!input) {
    if (sealed_)
      return std::make_error_code(std::errc::no_such_file_or_directory);
    return getUnderlyingFS().status(path);
  }
  if (input->error)
    return input->error;
  return llvm::vfs::Status::copyWithNewName(input->status, path);
}
bool CapturedFileSystem::exists(const llvm::Twine &path) {
  auto found = status(path);
  return found && found->exists();
}
llvm::ErrorOr<std::unique_ptr<llvm::vfs::File>>
CapturedFileSystem::openFileForRead(const llvm::Twine &path) {
  auto *captured = capture(path);
  if (captured && captured->error)
    return captured->error;
  if (!captured || !captured->bytes) {
    if (sealed_)
      return std::make_error_code(std::errc::no_such_file_or_directory);
    return getUnderlyingFS().openFileForRead(path);
  }
  auto input = *captured;
  input.status = llvm::vfs::Status::copyWithNewName(input.status, path);
  return std::unique_ptr<llvm::vfs::File>(
      std::make_unique<CapturedFile>(std::move(input)));
}
bool CapturedFileSystem::capture_entries(CapturedInput &input) {
  std::error_code error;
  auto iterator = getUnderlyingFS().dir_begin(input.lookup_path, error);
  if (error) {
    complete_ = false;
    return false;
  }
  std::vector<llvm::vfs::directory_entry> entries;
  for (llvm::vfs::directory_iterator end; iterator != end;
       iterator.increment(error)) {
    if (error || entries.size() >= max_inputs) {
      complete_ = false;
      return false;
    }
    entries.push_back(*iterator);
  }
  if (error) {
    complete_ = false;
    return false;
  }
  input.entries = std::move(entries);
  return true;
}
llvm::vfs::directory_iterator
CapturedFileSystem::dir_begin(const llvm::Twine &path, std::error_code &error) {
  auto *input = capture(path);
  if (!input || input->error || !input->status.isDirectory()) {
    if (!sealed_)
      return getUnderlyingFS().dir_begin(path, error);
    error = input && input->error
                ? input->error
                : std::make_error_code(std::errc::no_such_file_or_directory);
    return {};
  }
  if (!input->entries && (sealed_ || !capture_entries(*input))) {
    if (!sealed_)
      return getUnderlyingFS().dir_begin(path, error);
    error = std::make_error_code(std::errc::no_such_file_or_directory);
    return {};
  }
  error = {};
  return llvm::vfs::directory_iterator(
      std::make_shared<CapturedDirectory>(*input->entries));
}
std::error_code
CapturedFileSystem::getRealPath(const llvm::Twine &path,
                                llvm::SmallVectorImpl<char> &output) {
  auto *input = capture(path);
  if (!input) {
    if (!sealed_)
      return getUnderlyingFS().getRealPath(path, output);
    return std::make_error_code(std::errc::no_such_file_or_directory);
  }
  if (input->error)
    return input->error;
  if (input->real_path.empty())
    return std::make_error_code(std::errc::operation_not_permitted);
  output.assign(input->real_path.begin(), input->real_path.end());
  return {};
}
bool CapturedFileSystem::add_buffer(const std::string &path,
                                    llvm::StringRef bytes) {
  auto *input = capture(path);
  if (!input || input->error || !input->bytes || *input->bytes != bytes) {
    complete_ = false;
    return false;
  }
  return true;
}
bool CapturedFileSystem::validate() const {
  if (!complete_)
    return false;
  auto current = physical();
  for (const auto &[path, input] : inputs_) {
    if (input.staged)
      continue;
    auto *fresh = current->capture(input.lookup_path);
    if (!fresh || fresh->error != input.error)
      return false;
    for (const auto &alias : input.aliases)
      if (!current->capture(alias) || !current->complete_)
        return false;
    if (input.error)
      continue;
    if (fresh->real_path != input.real_path ||
        fresh->status.getType() != input.status.getType())
      return false;
    if (input.bytes && (!fresh->bytes || *fresh->bytes != *input.bytes))
      return false;
    if (input.entries) {
      if (!current->capture_entries(*fresh) ||
          namespace_digest(input) != namespace_digest(*fresh))
        return false;
    }
  }
  return true;
}
std::size_t CapturedFileSystem::estimated_bytes() const {
  std::size_t bytes = bytes_;
  for (const auto &[path, input] : inputs_) {
    bytes += sizeof(CapturedInput) + path.size() + input.lookup_path.size() +
             input.real_path.size() + 128;
    for (const auto &alias : input.aliases)
      bytes += sizeof(std::string) + alias.size();
    if (input.entries)
      for (const auto &entry : *input.entries)
        bytes += sizeof(entry) + entry.path().size();
  }
  return bytes;
}
llvm::IntrusiveRefCntPtr<CapturedFileSystem> CapturedFileSystem::restore(
    const std::vector<ctk::storage::StoredInput> &observations) {
  auto filesystem = physical();
  for (const auto &input : observations) {
    google::protobuf::Struct metadata;
    if (!google::protobuf::util::JsonStringToMessage(input.validation_context,
                                                     &metadata)
             .ok())
      return llvm::IntrusiveRefCntPtr<CapturedFileSystem>();
    const auto &fields = metadata.fields();
    if (fields.find("format") == fields.end() ||
        fields.at("format").string_value() != "ctk-filesystem-v2" ||
        fields.find("lookup_path") == fields.end() ||
        fields.find("real_path") == fields.end() ||
        fields.find("error") == fields.end() ||
        fields.find("enumerated") == fields.end())
      return llvm::IntrusiveRefCntPtr<CapturedFileSystem>();
    auto *captured =
        filesystem->capture(fields.at("lookup_path").string_value());
    if (!captured || captured->path != input.path ||
        captured->error.value() != fields.at("error").number_value())
      return llvm::IntrusiveRefCntPtr<CapturedFileSystem>();
    if (auto aliases = fields.find("aliases"); aliases != fields.end())
      for (const auto &alias : aliases->second.list_value().values())
        if (!filesystem->capture(alias.string_value()) ||
            !filesystem->complete_)
          return llvm::IntrusiveRefCntPtr<CapturedFileSystem>();
    if (input.kind == ctk::storage::ObservationKind::Absent) {
      if (!captured->error)
        return llvm::IntrusiveRefCntPtr<CapturedFileSystem>();
      continue;
    }
    if (captured->error ||
        captured->real_path != fields.at("real_path").string_value())
      return llvm::IntrusiveRefCntPtr<CapturedFileSystem>();
    if (input.kind == ctk::storage::ObservationKind::Content) {
      if (!captured->bytes ||
          content_digest(*captured->bytes) != input.digest_sha256.value_or(""))
        return llvm::IntrusiveRefCntPtr<CapturedFileSystem>();
    } else {
      if (!captured->status.isDirectory())
        return llvm::IntrusiveRefCntPtr<CapturedFileSystem>();
      if (fields.at("enumerated").bool_value() &&
          !filesystem->capture_entries(*captured))
        return llvm::IntrusiveRefCntPtr<CapturedFileSystem>();
      if (namespace_digest(*captured) != input.digest_sha256.value_or(""))
        return llvm::IntrusiveRefCntPtr<CapturedFileSystem>();
    }
  }
  if (filesystem->complete_)
    return filesystem;
  return llvm::IntrusiveRefCntPtr<CapturedFileSystem>();
}
} // namespace ctk::clang_layer::snapshot
