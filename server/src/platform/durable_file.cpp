#include "ctk/platform/durable_file.hpp"

#include <cerrno>
#include <fcntl.h>
#include <random>
#include <stdexcept>
#include <system_error>
#include <unistd.h>

namespace ctk::platform {
namespace {
class Descriptor final {
public:
  explicit Descriptor(int value) : value_(value) {
    if (value_ < 0)
      throw std::system_error(errno, std::generic_category(),
                              "open durable file");
  }
  ~Descriptor() { ::close(value_); }
  int get() const { return value_; }
  Descriptor(const Descriptor &) = delete;
  Descriptor &operator=(const Descriptor &) = delete;

private:
  int value_;
};
void synchronize(int descriptor) {
  while (::fsync(descriptor) != 0) {
    if (errno != EINTR)
      throw std::system_error(errno, std::generic_category(),
                              "sync durable file");
  }
}
} // namespace

void durable_atomic_write(const std::filesystem::path &path,
                          std::string_view bytes) {
  const auto destination = std::filesystem::absolute(path);
  const auto directory = destination.parent_path();
  std::filesystem::create_directories(directory);
  std::random_device random;
  const auto temporary = destination.string() + ".tmp-" +
                         std::to_string(random()) + "-" +
                         std::to_string(random());
  bool owns_temporary = false;
  try {
    {
      Descriptor file(::open(temporary.c_str(), O_WRONLY | O_CREAT | O_EXCL,
                             S_IRUSR | S_IWUSR));
      owns_temporary = true;
      std::size_t offset = 0;
      while (offset < bytes.size()) {
        const auto count =
            ::write(file.get(), bytes.data() + offset, bytes.size() - offset);
        if (count < 0) {
          if (errno == EINTR)
            continue;
          throw std::system_error(errno, std::generic_category(),
                                  "write durable file");
        }
        if (count == 0)
          throw std::runtime_error("durable file write made no progress");
        offset += static_cast<std::size_t>(count);
      }
      synchronize(file.get());
    }
    std::filesystem::rename(temporary, destination);
    owns_temporary = false;
    // Synchronize newly created parent entries as well as the replacement.
    // Resolving the existing directory also follows any parent symlinks.
    auto current = std::filesystem::canonical(directory);
    for (;;) {
      Descriptor parent(::open(current.c_str(), O_RDONLY | O_DIRECTORY));
      synchronize(parent.get());
      if (current == current.root_path())
        break;
      current = current.parent_path();
    }
  } catch (...) {
    if (owns_temporary) {
      std::error_code ignored;
      std::filesystem::remove(temporary, ignored);
    }
    throw;
  }
}
} // namespace ctk::platform
