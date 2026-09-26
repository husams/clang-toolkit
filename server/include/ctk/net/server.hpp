#pragma once

#include <string>

namespace ctk::net {

// Transport front-end (gRPC or REST, TBD). Dispatches requests to the core.
class Server {
 public:
  explicit Server(std::string address) : address_(std::move(address)) {}
  int run();

 private:
  std::string address_;
};

}  // namespace ctk::net
