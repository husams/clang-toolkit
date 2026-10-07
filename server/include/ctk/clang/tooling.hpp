#pragma once

#include <cstdint>
#include <functional>
#include <map>
#include <memory>
#include <string>
#include <vector>

#include "ctk/cache/snapshot.hpp"
#include "match/v1/match_result.pb.h"

namespace ctk::clang_layer {

// Thin wrapper over Clang C++ APIs: AST matchers, RecursiveASTVisitor
// traversal, CFG construction and call-graph building.
struct Project {
  std::string compile_commands_dir;
  std::vector<std::string> files;
};

struct FileInput {
  std::string path;
  std::vector<std::string> compile_arguments;
  std::string working_directory;
};

struct SemanticBinding {
  std::string kind;
  std::string name;
  std::string type;
  ctk::match::v1::MatchBinding value;
};

struct QueryResult {
  bool ok = false;
  bool cancelled = false;
  bool snapshot_retained = false;
  std::string profile;
  std::string message;
  std::uint64_t native_memory_bytes = 0;
  bool snapshot_evicted = false;
  bool storage_hit = false;
  std::string storage_message;
};

class IQueryEngine {
public:
  using Bindings = std::map<std::string, SemanticBinding>;
  using Checkpoint = std::function<bool()>;
  using MatchCallback = std::function<void(const Bindings &)>;

  virtual ~IQueryEngine() = default;
  virtual QueryResult match(const FileInput &file, const std::string &query,
                            const Checkpoint &checkpoint,
                            const MatchCallback &on_match) = 0;
  // Clang-free ownership for cursor execution. Existing injected query engines
  // need not implement retained matching.
  virtual ctk::cache::SnapshotPtr acquire_snapshot(const FileInput &) {
    return {};
  }
};

std::shared_ptr<IQueryEngine> make_query_engine();

std::vector<std::string> match(const Project &project,
                               const std::string &matcher);
std::string cfg(const Project &project, const std::string &function);
std::string callgraph(const Project &project);

} // namespace ctk::clang_layer
