#include "storage_internal.hpp"

#include <fcntl.h>
#include <unistd.h>
#ifdef __APPLE__
#include <sys/fcntl.h>
#endif

#include <array>
#include <cerrno>
#include <fstream>
#include <system_error>

namespace ctk::storage::detail {
namespace {

void write_all(int descriptor, std::string_view bytes) {
  std::size_t offset = 0;
  while (offset < bytes.size()) {
    const auto count = ::write(descriptor, bytes.data() + offset,
                               bytes.size() - offset);
    if (count < 0 && errno == EINTR)
      continue;
    if (count <= 0)
      throw std::system_error(errno, std::generic_category(), "write staged blob");
    offset += static_cast<std::size_t>(count);
  }
}

void sync_file(int descriptor) {
#ifdef __APPLE__
  if (::fcntl(descriptor, F_FULLFSYNC) == 0) return;
#endif
  if (::fsync(descriptor) != 0)
    throw std::system_error(errno, std::generic_category(), "sync staged blob");
}

Bytes read_file(const std::filesystem::path &path) {
  std::ifstream input(path, std::ios::binary);
  if (!input)
    throw std::runtime_error("cannot open native blob");
  return Bytes(std::istreambuf_iterator<char>(input), {});
}

} // namespace

BlobStore::BlobStore(std::filesystem::path root,
                     std::uint64_t max_artifact_bytes)
    : root_(std::move(root)), max_artifact_bytes_(max_artifact_bytes) {
  ensure_layout();
}

void BlobStore::ensure_layout() const {
  std::filesystem::create_directories(root_ / "blobs");
  std::filesystem::create_directories(root_ / "staging");
}

std::filesystem::path BlobStore::blob_path(std::string_view digest) const {
  validate_sha256(digest);
  return root_ / "blobs" / std::string(digest.substr(0, 2)) /
         std::string(digest.substr(2, 2)) / (std::string(digest) + ".ast");
}

void BlobStore::sync_directory(const std::filesystem::path &path) const {
  const int descriptor = ::open(path.c_str(), O_RDONLY);
  if (descriptor < 0)
    throw std::system_error(errno, std::generic_category(), "open directory for sync");
  const int result = ::fsync(descriptor);
  const int error_number = errno;
  ::close(descriptor);
  if (result != 0)
    throw std::system_error(error_number, std::generic_category(), "sync directory");
}

std::string BlobStore::publish(std::string_view bytes,
                               std::int64_t created_at_ms) {
  (void)created_at_ms;
  if (bytes.size() > max_artifact_bytes_)
    throw std::runtime_error("native artifact exceeds configured size limit");
  const auto digest = sha256(bytes);
  const auto destination = blob_path(digest);
  std::filesystem::create_directories(destination.parent_path());
  if (std::filesystem::exists(destination)) {
    const auto existing = read_file(destination);
    if (sha256(existing) != digest || existing != bytes)
      throw std::runtime_error("existing content-addressed blob failed byte verification");
    const int existing_descriptor = ::open(destination.c_str(), O_RDONLY);
    if (existing_descriptor < 0)
      throw std::system_error(errno, std::generic_category(), "open existing blob");
    try {
      sync_file(existing_descriptor);
    } catch (...) {
      ::close(existing_descriptor);
      throw;
    }
    if (::close(existing_descriptor) != 0)
      throw std::system_error(errno, std::generic_category(), "close existing blob");
    for (auto directory = destination.parent_path();;
         directory = directory.parent_path()) {
      sync_directory(directory);
      if (directory == root_) break;
    }
    return digest;
  }

  auto temporary_template = (root_ / "staging" / "blob-XXXXXX").string();
  std::vector<char> temporary_buffer(temporary_template.begin(),
                                     temporary_template.end());
  temporary_buffer.push_back('\0');
  const int descriptor = ::mkstemp(temporary_buffer.data());
  if (descriptor < 0)
    throw std::system_error(errno, std::generic_category(), "create staged blob");
  const std::filesystem::path temporary(temporary_buffer.data());
  int open_descriptor = descriptor;
  try {
    write_all(descriptor, bytes);
    sync_file(descriptor);
    const int close_result = ::close(descriptor);
    open_descriptor = -1;
    if (close_result != 0)
      throw std::system_error(errno, std::generic_category(), "close staged blob");
    if (::link(temporary.c_str(), destination.c_str()) != 0) {
      if (errno != EEXIST)
        throw std::system_error(errno, std::generic_category(), "publish native blob");
      const auto existing = read_file(destination);
      if (sha256(existing) != digest || existing != bytes)
        throw std::runtime_error("concurrent blob publication failed byte verification");
    }
    if (::unlink(temporary.c_str()) != 0)
      throw std::system_error(errno, std::generic_category(), "remove staged blob link");
    for (auto directory = destination.parent_path();;
         directory = directory.parent_path()) {
      sync_directory(directory);
      if (directory == root_) break;
    }
    sync_directory(root_ / "staging");
  } catch (...) {
    if (open_descriptor >= 0) ::close(open_descriptor);
    std::error_code ignored;
    std::filesystem::remove(temporary, ignored);
    throw;
  }
  return digest;
}

Bytes BlobStore::read(std::string_view digest, std::uint64_t expected_size) const {
  const auto path = blob_path(digest);
  const auto bytes = read_file(path);
  if (bytes.size() != expected_size || sha256(bytes) != digest)
    throw std::runtime_error("native blob integrity check failed");
  return bytes;
}

void BlobStore::remove(std::string_view digest) const {
  const auto path = blob_path(digest);
  std::error_code error;
  std::filesystem::remove(path, error);
  if (error)
    throw std::system_error(error, "remove native blob");
  if (std::filesystem::exists(path.parent_path()))
    sync_directory(path.parent_path());
}

std::uint64_t BlobStore::physical_bytes(std::size_t budget) const {
  std::uint64_t total = 0;
  std::size_t visited = 0;
  for (const auto &directory : {root_ / "blobs", root_ / "staging"}) {
    if (!std::filesystem::exists(directory)) continue;
    for (const auto &entry : std::filesystem::recursive_directory_iterator(directory)) {
      if (++visited > budget)
        throw std::runtime_error("physical-byte accounting exceeded its budget");
      if (entry.is_regular_file()) total += entry.file_size();
    }
  }
  return total;
}

std::size_t BlobStore::clean_staging(std::size_t budget) const {
  std::size_t visited = 0;
  std::size_t removed = 0;
  for (const auto &entry : std::filesystem::directory_iterator(root_ / "staging")) {
    if (visited++ >= budget)
      break;
    if (entry.is_regular_file() && std::filesystem::remove(entry.path()))
      ++removed;
  }
  return removed;
}

std::size_t BlobStore::clean_orphans(
    const std::function<bool(std::string_view)> &is_referenced,
    std::size_t budget) const {
  std::size_t removed = 0;
  std::size_t visited = 0;
  const auto root = root_ / "blobs";
  for (const auto &entry : std::filesystem::recursive_directory_iterator(root)) {
    if (visited++ >= budget)
      break;
    if (!entry.is_regular_file() || entry.path().extension() != ".ast")
      continue;
    const auto digest = entry.path().stem().string();
    if (!is_referenced(digest) && std::filesystem::remove(entry.path()))
      ++removed;
  }
  return removed;
}

} // namespace ctk::storage::detail
