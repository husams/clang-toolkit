#pragma once

#include <string>

namespace ctk::script {

// Embedded scripting engine used to compose matcher/traversal/CFG queries.
class Engine {
 public:
  std::string eval(const std::string& source);
};

}  // namespace ctk::script
