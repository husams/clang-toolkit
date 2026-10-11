#pragma once
#include "ctk/script/error.hpp"
#include "ctk/script/value.hpp"
#include <cstdint>
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
  virtual Value files(const std::string &) {
    throw Error(ctk::clang_layer::MatchCode::FailedPrecondition,
                "native file discovery is unavailable");
  }
  virtual void begin_batch_group(const Value &, std::size_t, std::size_t,
                                 std::uint64_t) {}
  virtual void end_batch_group(bool) {}
  virtual Value save(const std::string &, const Value &, const std::string &) {
    throw Error(ctk::clang_layer::MatchCode::FailedPrecondition,
                "native script export is unavailable");
  }
};
} // namespace ctk::script
