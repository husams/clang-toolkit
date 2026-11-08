#pragma once

#include "values.hpp"

#include <optional>

#include <llvm/Support/Error.h>
#include <llvm/Support/JSON.h>

namespace google::protobuf {
class Message;
}

namespace ctk::jit {

using SemanticHandle = std::shared_ptr<SemanticValue>;

SemanticHandle semantic(std::unique_ptr<google::protobuf::Message> message,
                        bool file_handle = false);
bool semantic_has_live_resource(const Value& value);
SemanticHandle semantic(const NativeNode& node);
SemanticHandle streamed_binding(const NativeNode& node,
                                const std::optional<std::string>& source_file);
bool is_streamed_binding(const Value& value);
std::optional<std::string> native_source_file(const AstHandle& ast);
llvm::Expected<llvm::json::Object> match_row_snapshot(const Record& row);
SemanticHandle semantic_graph(std::unique_ptr<google::protobuf::Message> message,
                              std::vector<std::shared_ptr<NativeNode>> nodes);
const google::protobuf::Message* semantic_message(const Value& value);
const NativeNode* retained_node(const Value& value);
std::optional<std::size_t> semantic_length(const Value& value);
std::optional<Value> semantic_iteration(const Value& value);
llvm::Expected<Value> semantic_field(const SemanticValue& value, llvm::StringRef name);
llvm::Expected<Value> semantic_method(const SemanticValue& value, llvm::StringRef name,
                                      const Sequence& arguments, Values* runtime = nullptr);
bool semantic_kind(const SemanticValue& value, llvm::StringRef kind);
llvm::Expected<llvm::json::Object> semantic_snapshot(const SemanticValue& value,
                                                     llvm::StringRef only_field = {});
llvm::Expected<Value> restore_semantic_snapshot(const llvm::json::Object& snapshot);
std::string semantic_json(const SemanticValue& value, bool indented);

} // namespace ctk::jit
