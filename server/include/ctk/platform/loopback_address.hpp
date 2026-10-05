#pragma once

#include <optional>
#include <string>
#include <string_view>

namespace ctk::platform {

// Returns a gRPC-ready spelling for localhost, IPv4 127/8, or IPv6 ::1.
std::optional<std::string> normalize_loopback_address(std::string_view host);

} // namespace ctk::platform
