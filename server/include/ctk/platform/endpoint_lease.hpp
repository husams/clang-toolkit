#pragma once
#include <string>

namespace ctk::platform {
// Process ownership only: this never creates, binds or unlinks a socket.
class EndpointLease {
public:
  explicit EndpointLease(const std::string &endpoint);
  ~EndpointLease();
  EndpointLease(const EndpointLease &) = delete;
  EndpointLease &operator=(const EndpointLease &) = delete;

private:
  int descriptor_{-1};
};
} // namespace ctk::platform
