#include "ctk/net/server.hpp"

int main(int argc, char** argv) {
  ctk::net::Server server(argc > 1 ? argv[1] : "127.0.0.1:7878");
  return server.run();
}
