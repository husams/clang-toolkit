#include "ctk/net/server.hpp"

#include <iostream>

namespace ctk::net {

int Server::run() {
  std::cout << "ctk-server listening on " << address_ << " (transport TBD)\n";
  return 0;
}

}  // namespace ctk::net
