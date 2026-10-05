#include "ctk/platform/loopback_address.hpp"

#include <arpa/inet.h>

#include <array>
#include <cstring>
#include <string>

namespace ctk::platform {

std::optional<std::string> normalize_loopback_address(std::string_view host) {
  if (host == "localhost")
    return "localhost";
  if (host.empty() || host.find('\0') != std::string_view::npos)
    return std::nullopt;

  std::string bare(host);
  const bool bracketed =
      bare.size() >= 2 && bare.front() == '[' && bare.back() == ']';
  if (bracketed)
    bare = bare.substr(1, bare.size() - 2);
  if (bare.find('[') != std::string::npos ||
      bare.find(']') != std::string::npos)
    return std::nullopt;

  in_addr ipv4{};
  if (inet_pton(AF_INET, bare.c_str(), &ipv4) == 1) {
    const auto *bytes = reinterpret_cast<const unsigned char *>(&ipv4);
    if (bytes[0] != 127)
      return std::nullopt;
    std::array<char, INET_ADDRSTRLEN> output{};
    if (!inet_ntop(AF_INET, &ipv4, output.data(), output.size()))
      return std::nullopt;
    return std::string(output.data());
  }

  in6_addr ipv6{};
  if (inet_pton(AF_INET6, bare.c_str(), &ipv6) != 1 ||
      !IN6_IS_ADDR_LOOPBACK(&ipv6))
    return std::nullopt;
  std::array<char, INET6_ADDRSTRLEN> output{};
  if (!inet_ntop(AF_INET6, &ipv6, output.data(), output.size()))
    return std::nullopt;
  return "[" + std::string(output.data()) + "]";
}

} // namespace ctk::platform
