#include "storage_internal.hpp"

#include <openssl/evp.h>

#include <array>
#include <cctype>
#include <stdexcept>

namespace ctk::storage::detail {

std::string sha256(std::string_view bytes) {
  std::array<unsigned char, EVP_MAX_MD_SIZE> digest{};
  unsigned int size = 0;
  if (EVP_Digest(bytes.data(), bytes.size(), digest.data(), &size, EVP_sha256(),
                 nullptr) != 1 || size != 32)
    throw std::runtime_error("SHA-256 calculation failed");
  constexpr char digits[] = "0123456789abcdef";
  std::string result(64, '0');
  for (std::size_t index = 0; index < size; ++index) {
    result[index * 2] = digits[digest[index] >> 4];
    result[index * 2 + 1] = digits[digest[index] & 0x0f];
  }
  return result;
}

std::string validate_sha256(std::string_view digest) {
  if (digest.size() != 64)
    throw std::invalid_argument("SHA-256 digest must contain 64 characters");
  for (const auto character : digest)
    if (!std::isdigit(static_cast<unsigned char>(character)) &&
        (character < 'a' || character > 'f'))
      throw std::invalid_argument("SHA-256 digest must be lowercase hexadecimal");
  return std::string(digest);
}

void validate_path(std::string_view path) {
  if (path.empty() || path.front() != '/' || path.find('\0') != path.npos ||
      path.find("//") != path.npos)
    throw std::invalid_argument("storage paths must be absolute canonical paths");
  std::size_t begin = 1;
  while (begin < path.size()) {
    const auto end = path.find('/', begin);
    const auto component = path.substr(
        begin, end == path.npos ? path.size() - begin : end - begin);
    if (component == "." || component == "..")
      throw std::invalid_argument("storage paths may not contain dot components");
    if (end == path.npos)
      break;
    begin = end + 1;
  }
}

} // namespace ctk::storage::detail
