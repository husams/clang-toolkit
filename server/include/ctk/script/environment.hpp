#pragma once
#include "ctk/script/error.hpp"
#include "ctk/script/value.hpp"
#include <map>
namespace ctk::script {
class Environment {
public:
  virtual ~Environment() = default;
  virtual Value call(const std::string &function,
                     const std::vector<Value> &arguments,
                     const std::map<std::string, Value> &options) = 0;
  virtual Value parse_file(const std::string &) {
    throw Error(ctk::clang_layer::MatchCode::FailedPrecondition,
                "native script parsing is unavailable");
  }
  virtual Value match(const std::string &, const Value *, const std::string &) {
    throw Error(ctk::clang_layer::MatchCode::FailedPrecondition,
                "native script matching is unavailable");
  }
  virtual Value match(const std::string &query, const Value *target,
                      const std::string &binding,
                      const std::map<std::string, Value> &options) {
    if (!options.empty())
      throw Error(ctk::clang_layer::MatchCode::InvalidArgument,
                  "native script matcher options are unavailable");
    return match(query, target, binding);
  }
};
} // namespace ctk::script
