#pragma once

#include "ctk/clang/tooling.hpp"
#include "match/v1/resources.pb.h"
#include <functional>
#include <stdexcept>

namespace ctk::clang_layer {
class ProfileMismatch final : public std::runtime_error {
public:
  using std::runtime_error::runtime_error;
};
struct ResolvedFileDescriptor {
  FileInput file;
  ctk::match::v1::InputDescriptor descriptor;
};
// Uses the same configured toolchain/defaults/environment as native
// acquisition, with the source spelling omitted from the profile's canonical
// identity.
std::string resolved_compilation_profile(const FileInput &file);
ResolvedFileDescriptor
resolve_file_descriptor(const ctk::match::v1::InputDescriptor &input);
ctk::match::v1::DiscoverFilesResponse discover_file_descriptors(
    const ctk::match::v1::DiscoverFilesRequest &request,
    const std::function<bool()> &checkpoint = [] { return true; });
inline constexpr std::uint64_t max_manifest_inputs = 10000;
inline constexpr std::uint64_t max_manifest_bytes = 16ULL * 1024 * 1024;
inline constexpr std::uint64_t max_discovery_entries = 100000;
} // namespace ctk::clang_layer
