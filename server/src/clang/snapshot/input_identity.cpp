#include "input_identity.hpp"
#include "ctk/cache/compilation_context.hpp"
#include <algorithm>
#include <google/protobuf/struct.pb.h>
#include <google/protobuf/util/json_util.h>
#include <llvm/Support/SHA256.h>
namespace ctk::clang_layer::snapshot {
std::string content_digest(llvm::StringRef bytes) {
  static constexpr char digits[] = "0123456789abcdef";
  llvm::SHA256 hash;
  hash.update(bytes);
  const auto digest = hash.final();
  std::string result;
  for (const auto byte : digest) {
    result.push_back(digits[byte >> 4]);
    result.push_back(digits[byte & 15]);
  }
  return result;
}
std::string namespace_digest(const CapturedInput &input) {
  std::string identity =
      "ctk-directory-v2:" + ctk::cache::canonical_json_string(input.real_path);
  if (input.entries) {
    std::vector<std::string> entries;
    for (const auto &entry : *input.entries)
      entries.push_back(ctk::cache::canonical_json_string(entry.path().str()) +
                        ":" + std::to_string(static_cast<int>(entry.type())));
    std::ranges::sort(entries);
    for (const auto &entry : entries)
      identity += '\n' + entry;
  } else
    identity += "\npresence";
  return content_digest(identity);
}
static std::string validation_context(const CapturedInput &input) {
  google::protobuf::Struct value;
  auto &fields = *value.mutable_fields();
  fields["format"].set_string_value("ctk-filesystem-v2");
  fields["lookup_path"].set_string_value(input.lookup_path);
  fields["real_path"].set_string_value(input.real_path);
  fields["error"].set_number_value(input.error.value());
  fields["enumerated"].set_bool_value(input.entries.has_value());
  for (const auto &alias : input.aliases)
    fields["aliases"].mutable_list_value()->add_values()->set_string_value(
        alias);
  std::string json;
  if (!google::protobuf::util::MessageToJsonString(value, &json).ok())
    throw std::runtime_error("input observation encoding failed");
  return json;
}
ctk::cache::InputObservation cache_observation(const CapturedInput &input) {
  ctk::cache::InputObservation result;
  result.path = input.path;
  result.validation_context = validation_context(input);
  if (input.error)
    result.kind = ctk::cache::InputKind::Absent;
  else if (input.status.isDirectory()) {
    result.kind = ctk::cache::InputKind::Directory;
    result.content_digest = namespace_digest(input);
  } else {
    result.kind = ctk::cache::InputKind::File;
    result.content_digest = content_digest(*input.bytes);
  }
  return result;
}
ctk::storage::InputObservation
stored_observation(const CapturedInput &input, ctk::storage::InputRole role) {
  const auto cached = cache_observation(input);
  ctk::storage::InputObservation result;
  result.path = input.path;
  result.role = role;
  result.validation_context = cached.validation_context;
  if (input.error)
    result.kind = ctk::storage::ObservationKind::Absent;
  else {
    result.kind = input.status.isDirectory()
                      ? ctk::storage::ObservationKind::Directory
                      : ctk::storage::ObservationKind::Content;
    result.digest_sha256 = cached.content_digest;
    result.mtime_ns =
        std::chrono::duration_cast<std::chrono::nanoseconds>(
            input.status.getLastModificationTime().time_since_epoch())
            .count();
    if (input.bytes)
      result.size_bytes = input.bytes->size();
  }
  return result;
}
} // namespace ctk::clang_layer::snapshot
