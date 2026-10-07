#pragma once
#include "captured_input.hpp"
#include "ctk/cache/snapshot.hpp"
#include "ctk/storage/store.hpp"
namespace ctk::clang_layer::snapshot {
std::string content_digest(llvm::StringRef bytes);
std::string namespace_digest(const CapturedInput &input);
ctk::cache::InputObservation cache_observation(const CapturedInput &input);
ctk::storage::InputObservation stored_observation(const CapturedInput &input,
                                                  ctk::storage::InputRole role);
} // namespace ctk::clang_layer::snapshot
