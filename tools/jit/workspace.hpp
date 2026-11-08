#pragma once

#include <deque>
#include <functional>

#include <llvm/Support/JSON.h>

#include "values.hpp"

namespace google::protobuf {
class Message;
}

namespace ctk::jit {

llvm::json::Value preview_message(const google::protobuf::Message& message);
llvm::json::Value preview_value(const Value& value);

class Workspace {
public:
  using EventSink = std::function<void(llvm::json::Object)>;

  Workspace(const Bindings& bindings, EventSink events)
      : bindings(bindings)
      , events(std::move(events)) {}

  void progress(llvm::json::Object event) const;
  void durable(const google::protobuf::Message& run) const;

  bool capture(Values& runtime, llvm::StringRef kind, const Value& value, llvm::StringRef key = {});
  llvm::json::Value outline(const llvm::json::Object& request) const;

private:
  struct Result {
    std::int64_t id;
    std::string kind;
    Value value;
  };

  const Bindings& bindings;
  EventSink events;
  std::deque<Result> results;
  std::int64_t next_id = 0;
};

} // namespace ctk::jit
