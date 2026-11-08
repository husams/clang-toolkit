#pragma once

#include "values.hpp"

#include <functional>

namespace ctk::application {
class MatchController;
class ScriptController;
} // namespace ctk::application

namespace ctk::clang_layer {
class IQueryEngine;
}

namespace ctk::index::v1 {
class ListProjectIndexesResponse;
}

namespace ctk::jit {

std::string new_batch_id();
std::uint64_t parse_batch_memory(llvm::StringRef text);

class EmbeddedServices {
public:
  using EventSink = std::function<void(std::string)>;

  EmbeddedServices(std::shared_ptr<clang_layer::IQueryEngine> engine,
                   application::MatchController& matches, EventSink events);
  ~EmbeddedServices();

  const Value* execute(Values& runtime, llvm::StringRef command, const Sequence& arguments,
                       llvm::StringRef options, const LocalState& settings, bool display);
  application::ScriptController& scripts();
  void finish();
  bool index_status(index::v1::ListProjectIndexesResponse& response) const;

private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};

} // namespace ctk::jit
