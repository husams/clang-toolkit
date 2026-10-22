#pragma once

#include "match/v1/parse_request.pb.h"
#include <memory>

namespace ctk::clang_layer {

struct PreparedCppSnippet {
  ctk::match::v1::ParseRequest request;
  std::shared_ptr<const void> lifetime;
};

// Materialize a private temporary .cpp and freeze the selected compilation
// environment. The lifetime must be attached to the resulting native snapshot.
PreparedCppSnippet
prepare_cpp_snippet(const ctk::match::v1::ParseRequest &request);

} // namespace ctk::clang_layer
